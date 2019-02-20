import configparser
import json
import multiprocessing as mp
import os
import queue
import sys
import time

import cv2
from flask import Blueprint, request

# get current file dir
sup = os.path.dirname(os.path.realpath(__file__))
sup = os.path.dirname(sup)
if sup not in sys.path:
    sys.path.append(sup)

from .error import *
from .param_tool import check_param_key, update_param, check_param_value, CAM_RE

from util import Face
from util import Log
from util import Kafka
from util import WeedClient
from util import mat_to_base64, base64_to_bytes, GrabJob, get_db_client

logger = Log('camera', 'logs/')
config = configparser.ConfigParser()
config.read('./app.config')
bp_camera = Blueprint('camera', __name__)
proc_pool = {}

track_internal = 3  # 跟踪间隔， 3秒


def grab_proc(url, rate, camera_id):
    '''
    抓图处理进程
    :param url:
    :param rate:
    :param camera_id:
    :param logger:
    :return:
    '''
    logger = Log('grab-proc' + str(os.getpid()), 'logs/')
    logger.info('初始化seaweedfs')
    master = WeedClient(config.get('weed', 'host'), config.getint('weed', 'port'))
    logger.info('初始化Kafka')
    kafka = Kafka(bootstrap_servers=config.get('kafka', 'boot_servers'))
    topic = config.get('camera', 'topic')
    face_tool = Face(config.get('api', 'face_server'))
    detect_count = 0  # 用于detect频次计数
    frame_internal = track_internal * rate
    trackable = False

    # 启动抓图线程
    q = queue.Queue(maxsize=100)
    t = GrabJob(q, camera_id, url, rate, Log('grab-proc' + str(os.getpid()) + '-thread', 'logs/'), config)
    t.start()
    while True:
        try:
            img = q.get(timeout=300)
            if detect_count % frame_internal == 0:
                detect_count = 0
                b64 = mat_to_base64(img)
                t1 = time.time()
                detect_result = face_tool.detect(b64)
                logger.info('detect cost time: ', round((time.time() - t1) * 1000), 'ms')
                if detect_result['error_message'] != '601':
                    logger.warning('verifier detector error, error_message:', detect_result['error_message'])
                    continue
                tracker = cv2.MultiTracker_create()
                latest_imgs = []
                timestamp = round(time.time())
                for face_num in range(detect_result['detect_nums']):
                    tmp = detect_result['detect'][face_num]
                    bbox = (tmp['left'], tmp['top'], tmp['width'], tmp['height'])
                    tracker.add(cv2.TrackerKCF_create(), img, bbox)
                    face_b64 = face_tool.crop(bbox[0], bbox[1], bbox[2], bbox[3], b64, True)
                    latest_img = {'image_base64': face_b64, 'bbox': bbox,
                                  'landmark': detect_result['detect'][face_num]['landmark'], 'time': timestamp}
                    # 增加人脸质量过滤
                    if tmp['sideFace'] == 0 and tmp['quality'] == 1 and tmp['score'] > 0.95:
                        latest_imgs.append(latest_img)
                if len(latest_imgs) > 0:
                    trackable = True
                else:
                    trackable = False

            elif trackable:
                # 开始追踪
                ok, bboxs = tracker.update(img)
                if ok and detect_count < frame_internal - 1:
                    if detect_count % 10 == 0:
                        logger.info('tracking..., detect_count = %d' % detect_count)
                    detect_count += 1
                    continue
                else:
                    # 取detect到的人脸
                    logger.info('tracking over! detect_count = %d' % detect_count)
                    for latest in latest_imgs:
                        logger.info([camera_id], 'track person success!')
                        face_b64 = latest['image_base64']

                        # save img to seaweed fs
                        logger.info([camera_id], 'save grabbed detect_result to seaweed fs')
                        assign = master.assign()
                        logger.info([camera_id], 'assign result:', assign)

                        ret = master.upload(assign['url'], assign['fid'], base64_to_bytes(face_b64),
                                            assign['fid'] + '.jpg')
                        logger.info([camera_id], 'upload result:', ret)

                        # send to Kafka
                        url = 'http' + ':' + '//' + assign['url'] + '/' + assign['fid']
                        logger.info('[', camera_id, ']', 'img url:', url)
                        msg = json.dumps({'url': url, 'time': latest['time'], 'camera_id': camera_id,
                                          'landmark': latest['landmark']})
                        logger.info([camera_id], 'send to kafka: ', msg)
                        kafka.send(topic, msg)
                    # 再次进入detect
                    detect_count = 0
                    trackable = False
                    logger.info('restart detection')
            else:
                if detect_count % 10 == 0:
                    logger.info('detect 0 detect_result, do not track', 'detect count= ', detect_count)
                detect_count += 1
                continue
        except queue.Empty:
            logger.error('grab queue empty error, exit')
            break
        detect_count += 1
    logger.info('抓图进程终止')


def watch_dog(logger):
    # 定时重启process_pool 中的抓图进程
    logger.info('process_pool status check start ...')
    for id, process in proc_pool.items():
        if not process.is_alive():
            process.start()
            logger.info('restart grab progress, camera_id = %s' % id)
    logger.info('proc_pool status: ', proc_pool)
    logger.info('process_pool status check end ...')


@bp_camera.route('/add', methods=['POST'])
def add():
    '''
    添加摄像头
    :return:
    '''
    start = time.time()
    db = get_db_client(config, logger)
    data = request.data.decode('utf-8')
    necessary_params = {'url'}
    default_params = {'rate': 1, 'grab': 1, 'name': 'Default Camera'}
    ret = {'time_used': 0, 'rtn': -1, 'id': -1}
    # 检查json 格式
    try:
        data = json.loads(data)
    except json.JSONDecodeError:
        logger.warning(GLOBAL_ERR['json_syntax_err'])
        ret['message'] = GLOBAL_ERR['json_syntax_err']
        return json.dumps(ret)
    legal = check_param_key(set(data), necessary_params, set(default_params))
    if not legal:
        logger.warning(GLOBAL_ERR['param_err'])
        ret['message'] = GLOBAL_ERR['param_err']
        return json.dumps(ret)
    legal = check_param_value([CAM_RE['url'], CAM_RE['rate'], CAM_RE['name']],
                              [data['url'], data['rate'], data['name']])
    if not legal:
        logger.warning(GLOBAL_ERR['value_err'])
        ret['message'] = GLOBAL_ERR['value_err']
        return json.dumps(ret)
    data = update_param(default_params, data)

    # 1. 存到数据库

    sql = "insert into `t_camera` (`name`, `url`, `rate`, `grab`) values (%s, %s, %s, %s)"
    camera_id = db.insert(sql, (data['name'], data['url'], data['rate'], data['grab']))
    ret['id'] = camera_id
    if camera_id == -1:
        logger.warning('添加摄像头失败')
        ret['rtn'] = -2
        ret['message'] = CAM_ERR['fail']
    else:
        logger.info('添加摄像头成功')
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['rtn'] = 0
        ret['message'] = CAM_ERR['success']

        # 启动抓图进程
        if data['grab'] == 1:
            try:
                p = mp.Process(target=grab_proc, args=(data['url'], data['rate'], camera_id))
                p.daemon = True
                p.start()
                proc_pool[camera_id] = p
                time.sleep(0.01)
                db.commit()
                logger.info('grab process start successfully, url = %s' % data['url'])
            except RuntimeError as e:
                logger.error('grab process runtime exception:', e)
                db.rollback()
                logger.info('add camera operation rollback...')
                del proc_pool[camera_id]
        else:
            db.commit()
            logger.info('只添加摄像头，不抓图')
    logger.info('process_pool: ', proc_pool)
    logger.info('camera add api return: ', ret)
    db.close()
    return json.dumps(ret)


@bp_camera.route('/del', methods=['POST'])
def delete():
    '''
    删除摄像头
    :return:
    '''
    start = time.time()
    db = get_db_client(config, logger)
    data = request.data.decode('utf-8')
    nessary_params = {'id'}
    default_params = {}
    ret = {'time_used': 0, 'rtn': -1}
    try:
        data = json.loads(data)
    except json.JSONDecodeError:
        logger.warning(GLOBAL_ERR['json_syntax_err'])
        ret['message'] = GLOBAL_ERR['json_syntax_err']
        return json.dumps(ret)
    legal = check_param_key(set(data), nessary_params, set(default_params))
    if not legal:
        logger.warning(GLOBAL_ERR['param_err'])
        ret['message'] = GLOBAL_ERR['param_err']
        return json.dumps(ret)
    legal = check_param_value([CAM_RE['id']], [data['id']])
    if not legal:
        logger.warning(GLOBAL_ERR['value_err'])
        ret['message'] = GLOBAL_ERR['value_err']
        return json.dumps(ret)
    data = update_param(default_params, data)

    if data['id'] in proc_pool:
        logger.info('停止抓图!')
        proc_pool[data['id']].terminate()  # 停止抓图进程
        del proc_pool[data['id']]  # 删除对应的进程

    sql = "delete from `t_camera` where id = %s "
    result = db.delete(sql, (data['id']))
    if result:
        logger.info('摄像头删除成功')
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['rtn'] = 0
        ret['message'] = CAM_ERR['success']
        db.commit()

    else:
        logger.info('摄像头删除失败')
        ret['rtn'] = -2
        ret['message'] = CAM_ERR['fail']
    logger.info('process_pool:', proc_pool)
    logger.info('camera delete api return: ', ret)
    db.close()
    return json.dumps(ret)


@bp_camera.route('/update', methods=['POST'])
def update():
    '''
    更新摄像头
    :return:
    '''
    start = time.time()
    db = get_db_client(config, logger)
    data = request.data.decode('utf-8')
    nessary_params = {'url', 'id'}
    default_params = {'rate': 1, 'grab': 1, 'name': 'Default Camera'}
    ret = {'time_used': 0, 'rtn': -1}
    try:
        data = json.loads(data)
    except json.JSONDecodeError:
        logger.warning(GLOBAL_ERR['json_syntax_err'])
        ret['message'] = GLOBAL_ERR['json_syntax_err']
        return json.dumps(ret)
    legal = check_param_key(set(data), nessary_params, set(default_params))
    if not legal:
        logger.warning(GLOBAL_ERR['param_err'])
        ret['message'] = GLOBAL_ERR['param_err']
        return json.dumps(ret)
    legal = check_param_value([CAM_RE['url'], CAM_RE['rate'], CAM_RE['name'], CAM_RE['id']],
                              [data['url'], data['rate'], data['name'], data['id']])
    if not legal:
        logger.warning(GLOBAL_ERR['value_err'])
        ret['message'] = GLOBAL_ERR['value_err']
        return json.dumps(ret)
    data = update_param(default_params, data)
    camera_id = data['id']
    del data['id']
    result = False
    for key in data:
        sql = "update `t_camera` set `{}` = %s where id = %s".format(key)
        result = db.update(sql, (data[key], camera_id))
    if result:
        logger.info('摄像头更新成功')
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['rtn'] = 0
        ret['message'] = CAM_ERR['success']

        # 关闭原来的抓图
        if camera_id in proc_pool:
            logger.info('停止抓图!')
            proc_pool[camera_id].terminate()  # 停止抓图进程
            del proc_pool[camera_id]  # 删除对应的进程

        # 启动抓图进程
        if data['grab'] == 1:
            try:
                p = mp.Process(target=grab_proc, args=(data['url'], data['rate'], camera_id))
                p.daemon = True
                p.start()
                proc_pool[camera_id] = p
                logger.info('grab process start successfully, url = %s' % data['url'])
            except RuntimeError as e:
                logger.error('grab process runtime exception:', e)
                logger.info('add camera operation rollback...')
                del proc_pool[camera_id]
            finally:
                db.commit()

        else:
            db.commit()
            logger.info('只添加摄像头，不抓图')
    else:
        logger.info('摄像头更新失败')
        ret['rtn'] = -2
        ret['message'] = CAM_ERR['fail']

    logger.info('process_pool:', proc_pool)
    logger.info('camera update api return: ', ret)
    db.close()
    return json.dumps(ret)


@bp_camera.route('/status', methods=['POST'])
def state():
    '''
    查看摄像头状态
    :return:
    '''
    start = time.time()
    db = get_db_client(config, logger)
    data = request.data.decode('utf-8')
    nessary_params = {'id'}
    default_params = {}
    ret = {'time_used': 0, 'rtn': -1}
    try:
        data = json.loads(data)
    except json.JSONDecodeError:
        logger.warning(GLOBAL_ERR['json_syntax_err'])
        ret['message'] = GLOBAL_ERR['json_syntax_err']
        return json.dumps(ret)
    legal = check_param_key(set(data), nessary_params, set(default_params))
    if not legal:
        logger.warning(GLOBAL_ERR['param_err'])
        ret['message'] = GLOBAL_ERR['param_err']
        return json.dumps(ret)
    legal = check_param_value([CAM_RE['id']], [data['id']])
    if not legal:
        logger.warning(GLOBAL_ERR['value_err'])
        ret['message'] = GLOBAL_ERR['value_err']
        return json.dumps(ret)
    sql = "select state from `t_camera` where id = %s "
    result = db.select(sql, data['id'])
    if result is None:
        logger.warning('SQL select exception')
        ret['rtn'] = -2
        ret['message'] = GLOBAL_ERR['sql_select_err']
    elif len(result) == 0:
        logger.info('状态查询失败，找不到摄像头!')
        ret['rtn'] = 0
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['message'] = GLOBAL_ERR['null']
    else:
        logger.info('状态查询成功')
        ret['rtn'] = 0
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['message'] = CAM_ERR['success']
        ret['state'] = result[0][0]

    logger.info('process_pool:', proc_pool)
    logger.info('camera state api return: ', ret)
    db.close()
    return json.dumps(ret)


@bp_camera.route('/list', methods=['GET'])
def listall():
    '''
    输出所有摄像头信息
    :return:
    '''
    start = time.time()
    db = get_db_client(config, logger)
    ret = {'time_used': 0, 'rtn': -1}
    sql = "select `id`, `name` from t_camera"
    select_result = db.select(sql)
    if select_result is not None:
        logger.info('select from t_camera success')
        infos = []
        for item in select_result:
            info = {'id': item[0], 'name': item[1]}
            infos.append(info)
        ret['infos'] = infos
        ret['rtn'] = 0
        ret['time_used'] = round((time.time() - start) * 1000)
    else:
        logger.info('select from t_camera fail')

    logger.info('process_pool:', proc_pool)
    logger.info('camera state api return: ', ret)
    db.close()
    return json.dumps(ret, ensure_ascii=False)
