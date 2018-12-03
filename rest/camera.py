from flask import Blueprint, request
import json,time
from util.mysql import Mysql
from util.logger import Log
import configparser

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

class Camera:
    def __init__(self,url, rate = 1, grab = 1, name = 'Default Camera'):
        self.url = url
        self.rate = rate
        self.grab = grab
        self.name = name


@camera.route('/add', methods=['POST'])
def add():
    '''
    添加摄像头
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    data = json.loads(data)
    obj = Camera(data['url'])
    ret = {}
    for key in data.keys():
        print(key)
        obj.__setattr__(key, data[key])

    # 1. todo 抓图

    # 2. 存到数据库

    sql = "insert into `t_camera` (`name`, `url`, `rate`, `grab`) values (%s, %s, %s, %s)"
    camera_id = db.insert(sql, (obj.name, obj.url, obj.rate, obj.grab))
    ret['id'] = camera_id
    if camera_id == -1:
        logger.info('添加摄像头失败')
        ret['time_used'] = 0
        ret['rtn'] = -1
        ret['message'] = '摄像头添加失败'
    else:
        logger.info('添加摄像头成功')
        ret['time_used'] = round((time.time() - start)*1000)
        ret['rtn'] = 0
        ret['message'] = '摄像头添加成功'
    return json.dumps(ret)

@camera.route('/del', methods=['POST'])
def delete():
    '''
    删除摄像头
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    data = json.loads(data)
    sql = "delete from `t_camera` where id = %s "
    result = db.update(sql, (data['id']))
    ret = {}
    if result:
        logger.info('摄像头删除成功')
        ret['time_used'] = round((time.time() - start)*1000)
        ret['rnt'] = 0
        ret['message'] = '摄像头删除成功'
    else:
        logger.info('摄像头删除失败')
        ret['time_used'] = 0
        ret['rnt'] = -1
        ret['message'] = '摄像头删除失败'
    return json.dumps(ret)

@camera.route('/mod', methods=['POST'])
def update():
    '''
    更新摄像头
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    data = json.loads(data)
    camera_id = data['id']
    del data['id']
    print(data)
    print(camera_id)
    for key in data.keys():
        sql = "update `t_camera` set `{}` = %s where id = %s".format(key)
        result = db.update(sql, (data[key], camera_id))
        print((key, data[key], camera_id))
    ret = {}
    if result:
        logger.info('摄像头更新成功')
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['rnt'] = 0
        ret['message'] = '摄像头更新成功'
    else:
        logger.info('摄像头更新失败')
        ret['time_used'] = 0
        ret['rnt'] = -1
        ret['message'] = '摄像头更新失败'
    return json.dumps(ret)

