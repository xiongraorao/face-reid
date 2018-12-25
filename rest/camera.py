import configparser
import json
import multiprocessing as mp
import os
import sys
import time

from flask import Blueprint, request

# get current file dir
sup = os.path.dirname(os.path.realpath(__file__))
sup = os.path.dirname(sup)
if sup not in sys.path:
    sys.path.append(sup)

from .error import *
from .param_tool import check_param_key, update_param

from util import Face, mat_to_base64, base64_to_bytes
from util import Grab
from util import Log
from util import Kafka
from util import Mysql
from util import WeedClient

logger = Log('camera', 'logs/')
config = configparser.ConfigParser()
config.read('./app.config')

db = Mysql(host=config.get('db', 'host'),
           port=config.getint('db', 'port'),
           user=config.get('db', 'user'),
           password=config.get('db', 'password'),
           db=config.get('db', 'db'),
           charset=config.get('db', 'charset'))
db.set_logger(logger)

bp_camera = Blueprint('camera', __name__)

proc_pool = {}

def grab_proc(url, rate, camera_id):
    '''
    抓图处理进程
    :param url:
    :param rate:
    :param camera_id:
    :param logger:
    :return:
    '''
    logger = Log('grab-proc'+ str(os.getpid()), 'logs/')
    g = Grab(url, rate, logger=logger)
    # todo 根据g的 self.initErr 来判断摄像头的各种错误信息，需要操作数据库
    if g.initErr != 0:
        # 写入状态
        sql = 'update `t_camera` set state = %s where id = %s '
        ret = db.update(sql, (g.initErr, camera_id))
        if ret:
            logger.info([camera_id], '更新摄像头state成功')
        else:
            logger.info([camera_id], '更新摄像头state失败')
        logger.info([camera_id], '摄像头视频流初始化失败, %s ' % CAM_INIT_ERR[g.initErr])
        g.close()  # 关闭抓图进程
        return
    else:
        logger.info([camera_id], '摄像头视频流初始化正常')
    logger.info('初始化seaweedfs')
    master = WeedClient(config.get('weed', 'host'), config.getint('weed', 'port'))
    logger.info('初始化Kafka')
    kafka = Kafka(bootstrap_servers=config.get('kafka', 'boot_servers'))
    topic = config.get('camera', 'topic')
    # q = queue.Queue(1000)
    # job = GrabJob(grab=g, queue=q)
    # job.start()
    count = 0
    face_tool = Face(config.get('api','face_server'))
    while True:
        img = g.grab_image()
        if img is not None:
            # 检测人脸, 启用跟踪模式
            b64 = mat_to_base64(img)
            face = face_tool.detect(b64, field='track', camera_id=str(camera_id))
            for num in range(face['track_nums']):
                logger.info([camera_id], 'track person success! num = %d' % num)
                face_b64 = face['track'][num]['image_base64']

                # mat = base64_to_mat(detect_face)
                # cv2.imwrite(str(uuid.uuid4())+'.jpg', mat)
                # logger.info('detect_face: ', detect_face)

                # save img to seaweed fs
                logger.info([camera_id], 'save grabbed face to seaweed fs')
                assign = master.assign()
                logger.info([camera_id], 'assign result:', assign)
                # bs = cv2.imencode('.jpg', detect_face)

                ret = master.upload(assign['url'], assign['fid'], base64_to_bytes(face_b64), assign['fid'] + '.jpg')
                logger.info([camera_id], 'upload result:', ret)

                # send to Kafka
                url = 'http' + ':' + '//' + assign['url'] + '/' + assign['fid']
                logger.info('[', camera_id, ']', 'img url:', url)
                msg = json.dumps({'url': url, 'time': int(face['track'][num]['bestTime']), 'camera_id': camera_id,
                                  'landmark': face['track'][num]['landmark']})
                logger.info([camera_id], 'send to kafka: ', msg)
                kafka.send(topic, msg)
                count = 0
        else:
            count += 1
            if count > 50:  # 连续50帧抓不到图，则释放资源
                logger.warning('连续50帧抓图异常，退出抓图进程!')
                g.close()
                break
    logger.info('抓图进程终止')


@bp_camera.route('/add', methods=['POST'])
def add():
    '''
    添加摄像头
    :return:
    '''
    start = time.time()
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
    logger.debug('process_pool: ', proc_pool)
    logger.info('camera add api return: ', ret)
    return json.dumps(ret)


@bp_camera.route('/del', methods=['POST'])
def delete():
    '''
    删除摄像头
    :return:
    '''
    start = time.time()
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
    data = update_param(default_params, data)

    if data['id'] in proc_pool:
        logger.info('停止抓图!')
        proc_pool[data['id']].terminate()  # 停止抓图进程

    sql = "delete from `t_camera` where id = %s "
    result = db.delete(sql, (data['id']))
    if result:
        logger.info('摄像头删除成功')
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['rnt'] = 0
        ret['message'] = CAM_ERR['success']
        db.commit()

    else:
        logger.info('摄像头删除失败')
        ret['rnt'] = -2
        ret['message'] = CAM_ERR['fail']
    logger.debug('process_pool:', proc_pool)
    logger.info('camera delete api return: ', ret)
    return json.dumps(ret)


@bp_camera.route('/update', methods=['POST'])
def update():
    '''
    更新摄像头
    :return:
    '''
    start = time.time()
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
        ret['rnt'] = 0
        ret['message'] = CAM_ERR['success']

        # 关闭原来的抓图
        if camera_id in proc_pool:
            logger.info('停止抓图!')
            proc_pool[camera_id].terminate()  # 停止抓图进程

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
        ret['rnt'] = -2
        ret['message'] = CAM_ERR['fail']

    logger.debug('process_pool:', proc_pool)
    logger.info('camera update api return: ', ret)
    return json.dumps(ret)


@bp_camera.route('/status', methods=['POST'])
def state():
    '''
    查看摄像头状态
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    ret = {'time_used': 0, 'rtn': -1}
    try:
        data = json.loads(data)
    except json.JSONDecodeError:
        logger.warning(GLOBAL_ERR['json_syntax_err'])
        ret['message'] = GLOBAL_ERR['json_syntax_err']
        return json.dumps(ret)
    if 'id' not in data:
        logger.warning(GLOBAL_ERR['param_err'])
        ret['message'] = GLOBAL_ERR['param_err']
        return json.dumps(ret)
    camera_id = data['id']
    sql = "select state from `t_camera` where id = %s "
    result = db.select(sql, camera_id)
    if result is None:
        logger.warning('SQL select exception')
        ret['rtn'] = -2
        ret['message'] = GLOBAL_ERR['sql_select_err']
    elif len(result) == 0:
        logger.info('状态查询失败，找不到摄像头!')
        ret['rtn'] = 0
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['message'] = CAM_ERR['null']
    else:
        logger.info('状态查询成功')
        ret['rtn'] = 0
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['message'] = CAM_ERR['success']
        ret['state'] = result[0][0]

    logger.info('camera state api return: ', ret)
    return json.dumps(ret)