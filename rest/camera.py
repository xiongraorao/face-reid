from flask import Blueprint, request
import json,time
from util.mysql import Mysql
from util.logger import Log
from util.grab import Grab
from rest.error import *
from rest.http_util import check_param, update_param
import configparser
import multiprocessing as mp
from util.seaweed import WeedVolume, WeedMaster
from util.mykafka import Kafka
from util.grab_job import GrabJob
import queue
import cv2


camera = Blueprint('camera',__name__,)
logger = Log(__name__, is_save=False)
config = configparser.ConfigParser()
config.read('../app.config')
db = Mysql(host=config.get('db','host'),
                     port=config.getint('db','port'),
                     user=config.get('db', 'user'),
                     password=config.get('db','password'),
                     db=config.get('db','db'),
                     charset=config.get('db','charset'))
db.set_logger(logger)
default_param = {
    'rate': 1,
    'grab': 1,
    'name': 'Default Camera'
}

proc_pool = {}

def grab_proc(url, rate, camera_id, logger):
    g = Grab(url, rate)
    # todo 根据g的 self.initErr 来判断摄像头的各种错误信息，需要操作数据库
    master = WeedMaster(config.get('weed','m_host'), config.getint('weed', 'm_port'))
    volume = WeedVolume(config.get('weed','v_host'), config.getint('weed', 'v_port'))
    kafka = Kafka(bootstrap_servers=config.get('kafka', 'boot_servers'))
    topic = config.get('camera', 'topic')
    # q = queue.Queue(1000)
    # job = GrabJob(grab=g, queue=q)
    # job.start()
    while True:
        img = g.grab_image()
        timestamp = time.time()
        if img is not None:
            # save img to seaweed fs
            assign = master.assign()
            logger.debug('assign result: ' + assign)
            bs = cv2.imencode('.jpg', img)
            ret = volume.upload(assign['fid'], bs[1], assign['fid']+'.jpg')
            logger.info('upload result: ' + ret)

            # send to Kafka
            url = 'http' + ':' + '//' + assign['url'] + '/' + assign['fid']
            logger.debug('['+camera_id + ']' + ', img url: ' + url)
            msg = json.dumps({'url':url,'time':timestamp, 'camera': camera_id})
            logger.debug('send to kafka: ' + msg)
            kafka.produce(topic, msg)


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
    data = update_param(default_param, data)
    logger.debug('parameters: ' + data)

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
        ret['time_used'] = round((time.time() - start)*1000)
        ret['rtn'] = 0
        ret['message'] = CAM_ERR['success']

        # 启动抓图进程
        if data['grab'] == 1:
            proc_pool[camera_id] = mp.Process(target=grab_proc, args=(data['url'], data['rate'], camera_id, logger))
            logger.info('抓图进程启动完毕！')
        else:
            logger.info('只添加摄像头，不抓图')

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
    data = update_param(default_param, data)

    if data['id'] in proc_pool:
        logger.info('停止抓图!')
        proc_pool[data['id']].terminate() # 停止抓图进程

    sql = "delete from `t_camera` where id = %s "
    result = db.update(sql, (data['id']))
    if result:
        logger.info('摄像头删除成功')
        ret['time_used'] = round((time.time() - start)*1000)
        ret['rnt'] = 0
        ret['message'] = CAM_ERR['success']

    else:
        logger.info('摄像头删除失败')
        ret['time_used'] = 0
        ret['rnt'] = -1
        ret['message'] = CAM_ERR['fail']
    return json.dumps(ret)

@camera.route('/update', methods=['POST'])
def update():
    '''
    更新摄像头
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    nessary_params = {'url','id'}
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
    data = update_param(default_param, data)
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
        if data['id'] in proc_pool:
            logger.info('停止抓图!')
            proc_pool[data['id']].terminate()  # 停止抓图进程

        # 启动抓图进程
        if data['grab'] == 1:
            proc_pool[camera_id] = mp.Process(target=grab_proc, args=(data['url'], data['rate'], camera_id, logger))
            logger.info('抓图进程启动完毕！')
        else:
            logger.info('只添加摄像头，不抓图')
    else:
        logger.info('摄像头更新失败')
        ret['time_used'] = 0
        ret['rnt'] = -1
        ret['message'] = CAM_ERR['fail']
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



