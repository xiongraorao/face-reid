import configparser
import json
import multiprocessing as mp
import time

import cv2
from flask import Blueprint, request

from rest.error import *
from rest.http_util import check_param, update_param
from util.grab import Grab
from util.logger import Log
from util.mykafka import Kafka
from util.mysql import Mysql
from util.seaweed import WeedVolume, WeedMaster

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

camera = Blueprint('camera', __name__)

proc_pool = {}


def grab_proc(url, rate, camera_id, logger):
    '''
    抓图处理进程
    :param url:
    :param rate:
    :param camera_id:
    :param logger:
    :return:
    '''
    g = Grab(url, rate)
    # todo 根据g的 self.initErr 来判断摄像头的各种错误信息，需要操作数据库
    if g.initErr != 0:
        # 写入状态
        sql = 'update `t_camera` set state = %s where id = %s '
        ret = db.update(sql, (g.initErr, camera_id))
        if ret:
            logger.info('更新摄像头state成功')
        else:
            logger.info('更新摄像头state失败')
        logger.info('摄像头视频流初始化失败, %s ' % CAM_INIT_ERR[g.initErr])
        g.close()  # 关闭抓图进程
        return
    else:
        logger.info('摄像头视频流初始化正常')
    logger.info('初始化seaweedfs')
    master = WeedMaster(config.get('weed', 'm_host'), config.getint('weed', 'm_port'))
    volume = WeedVolume(config.get('weed', 'v_host'), config.getint('weed', 'v_port'))
    logger.info('初始化Kafka')
    kafka = Kafka(bootstrap_servers=config.get('kafka', 'boot_servers'))
    topic = config.get('camera', 'topic')
    # q = queue.Queue(1000)
    # job = GrabJob(grab=g, queue=q)
    # job.start()
    count = 0
    while True:
        img = g.grab_image()
        timestamp = time.time()
        if img is not None:
            # save img to seaweed fs
            assign = master.assign()
            logger.debug('assign result:', assign)
            bs = cv2.imencode('.jpg', img)
            ret = volume.upload(assign['fid'], bs[1], assign['fid'] + '.jpg')
            logger.info('upload result:', ret)

            # send to Kafka
            url = 'http' + ':' + '//' + assign['url'] + '/' + assign['fid']
            logger.debug('[', camera_id, ']', 'img url:', url)
            msg = json.dumps({'url': url, 'time': timestamp, 'camera': camera_id})
            logger.debug('send to kafka: ', msg)
            kafka.produce(topic, msg)
            count = 0
        else:
            count += 1
            if count > 50:  # 连续50帧抓不到图，则释放资源
                logger.warning('连续50帧抓图异常，退出抓图进程!')
                g.close()
                break
    logger.info('抓图进程终止')


@camera.route('/add', methods=['POST'])
def add():
    '''
    添加摄像头
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    nessary_params = {'url'}
    default_params = {'rate': 1, 'grab': 1, 'name': 'Default Camera'}
    ret = {'time_used': 0, 'rtn': -1, 'id': 'null'}
    # 检查json 格式
    try:
        data = json.loads(data)
    except json.JSONDecodeError:
        logger.warning(GLOBAL_ERR['json_syntax_err'])
        ret['message'] = GLOBAL_ERR['json_syntax_err']
        return json.dumps(ret)
    legal = check_param(set(data), nessary_params, set(default_params))
    if not legal:
        logger.warning(GLOBAL_ERR['param_err'])
        ret['message'] = GLOBAL_ERR['param_err']
        return json.dumps(ret)
    data = update_param(default_params, data)
    logger.debug('parameters: ', data)

    # 1. 存到数据库

    sql = "insert into `t_camera` (`name`, `url`, `rate`, `grab`) values (%s, %s, %s, %s)"
    camera_id = db.insert(sql, (data['name'], data['url'], data['rate'], data['grab']))
    ret['id'] = camera_id
    if camera_id == -1:
        logger.info('添加摄像头失败')
        ret['rtn'] = -2
        ret['message'] = CAM_ERR['success']
    else:
        logger.info('添加摄像头成功')
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['rtn'] = 0
        ret['message'] = CAM_ERR['success']

        # 启动抓图进程
        if data['grab'] == 1:
            try:
                p = mp.Process(target=grab_proc, args=(data['url'], data['rate'], camera_id, logger))
                p.daemon = True
                p.start()
                proc_pool[camera_id] = p
            except RuntimeError as e:
                logger.error('grab process runtime exception:', e)
                logger.info('mysql rollback')
                db.rollback()
                del proc_pool[camera_id]
            finally:
                logger.info('抓图进程启动完毕！')
                logger.info('mysql operation commit')
                db.commit()
        else:
            db.commit()
            logger.info('只添加摄像头，不抓图')
    logger.debug('process_pool: ', proc_pool)

    return json.dumps(ret)


@camera.route('/del', methods=['POST'])
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
    legal = check_param(set(data), nessary_params, set(default_params))
    if not legal:
        logger.warning(GLOBAL_ERR['param_err'])
        ret['message'] = GLOBAL_ERR['param_err']
        return json.dumps(ret)
    data = update_param(default_params, data)

    if data['id'] in proc_pool:
        logger.info('停止抓图!')
        proc_pool[data['id']].terminate()  # 停止抓图进程

    sql = "delete from `t_camera` where id = %s "
    result = db.update(sql, (data['id']))
    if result:
        logger.info('摄像头删除成功')
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['rnt'] = 0
        ret['message'] = CAM_ERR['success']
        db.commit()

    else:
        logger.info('摄像头删除失败')
        ret['time_used'] = 0
        ret['rnt'] = -1
        ret['message'] = CAM_ERR['fail']
    logger.debug('process_pool:', proc_pool)
    return json.dumps(ret)


@camera.route('/update', methods=['POST'])
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
    legal = check_param(set(data), nessary_params, set(default_params))
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
        db.commit()

        # 关闭原来的抓图
        if camera_id in proc_pool:
            logger.info('停止抓图!')
            proc_pool[camera_id].terminate()  # 停止抓图进程

        # 启动抓图进程
        if data['grab'] == 1:
            p = mp.Process(target=grab_proc, args=(data['url'], data['rate'], camera_id, logger))
            p.daemon = True
            p.start()
            proc_pool[camera_id] = p
            logger.info('抓图进程启动完毕！')
        else:
            logger.info('只添加摄像头，不抓图')
    else:
        logger.info('摄像头更新失败')
        ret['time_used'] = 0
        ret['rnt'] = -1
        ret['message'] = CAM_ERR['fail']
    logger.info('process_pool:', proc_pool)
    return json.dumps(ret)


@camera.route('/status', methods=['GET'])
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
    if len(result) == 0:
        logger.warning('状态查询失败，找不到摄像头!')
        ret['message'] = CAM_ERR['fail']
        return json.dumps(ret)
    else:
        logger.warning('状态查询成功')
        ret['message'] = CAM_ERR['success']
        ret['state'] = result[0][0]
        return json.dumps(ret)
