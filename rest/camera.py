from flask import Blueprint, request
import json,time
from util.mysql import Mysql
from util.logger import Log
from rest.error import *
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
default_param = {
    'rate': 1,
    'grab': 1,
    'name': 'Default Camera'
}

@camera.route('/add', methods=['POST'])
def add():
    '''
    添加摄像头
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    ret = {'time_used': 0, 'rtn': -1, 'id': 'null'}
    # 检查json 格式
    try:
        data = json.loads(data)
    except json.JSONDecodeError:
        logger.warning(GLOBAL_ERR['json_syntax_err'])
        ret['message'] = GLOBAL_ERR['json_syntax_err']
        return json.dumps(ret)
    # 检查参数合法性
    if 'url' not in data:
        logger.warning(GLOBAL_ERR['param_err'])
        ret['message'] = GLOBAL_ERR['param_err']
        return json.dumps(ret)
    # 更新参数
    params = default_param.copy()
    params.update(data)

    # 1. todo 抓图

    # 2. 存到数据库

    sql = "insert into `t_camera` (`name`, `url`, `rate`, `grab`) values (%s, %s, %s, %s)"
    camera_id = db.insert(sql, (params['name'], params['url'], params['rate'], params['grab']))
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
    return json.dumps(ret)

@camera.route('/del', methods=['POST'])
def delete():
    '''
    删除摄像头
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

@camera.route('/mod', methods=['POST'])
def update():
    '''
    更新摄像头
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
    if 'id' not in data or 'url' not in data:
        logger.warning(GLOBAL_ERR['param_err'])
        ret['message'] = GLOBAL_ERR['param_err']
        return json.dumps(ret)
    params = default_param.copy()
    params.update(data)
    camera_id = params['id']
    del params['id']
    result = False
    for key in params:
        sql = "update `t_camera` set `{}` = %s where id = %s".format(key)
        result = db.update(sql, (params[key], camera_id))
    if result:
        logger.info('摄像头更新成功')
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['rnt'] = 0
        ret['message'] = CAM_ERR['success']
    else:
        logger.info('摄像头更新失败')
        ret['time_used'] = 0
        ret['rnt'] = -1
        ret['message'] = CAM_ERR['fail']
    return json.dumps(ret)

@camera.route('/state', methods=['GET'])
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



