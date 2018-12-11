from flask import Blueprint, request
import json
import time
import multiprocessing as mp
from util.mysql import Mysql
from util.logger import Log
from rest.error import *
import configparser
from rest.http_util import check_param, update_param

logger = Log('search', 'logs/')
config = configparser.ConfigParser()
config.read('./app.config')

db = Mysql(host=config.get('db', 'host'),
           port=config.getint('db', 'port'),
           user=config.get('db', 'user'),
           password=config.get('db', 'password'),
           db=config.get('db', 'db'),
           charset=config.get('db', 'charset'))
db.set_logger(logger)

search = Blueprint('search', __name__)

proc_pool = {}

def search_proc(data, logger):
    '''
    查询进程，用于结果，并写入数据库
    :param data:
    :param logger:
    :return:
    '''
    pass

@search.route('/', methods=['POST'])
def search():
    '''
    人脸搜索，动态库检索
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    necessary_params = {'image_base64', 'start_pos', 'limit'}
    default_params = {'query_id': -1, 'camera_ids': 'all', 'topk':100}
    ret = {'time_used':0, 'rtn': -1, 'query_id': -1}
    try:
        data = json.loads(data)
    except json.JSONDecodeError:
        logger.warning(GLOBAL_ERR['json_syntax_err'])
        ret['message'] = GLOBAL_ERR['json_syntax_err']
        return json.dumps(ret)

    legal = check_param(set(data), necessary_params, set(default_params))
    if not legal:
        logger.warning(GLOBAL_ERR['param_err'])
        ret['message'] = GLOBAL_ERR['param_err']
        return json.dumps(ret)
    data = update_param(default_params, data)
    logger.info('parameters:', data)

    # 1. 启动查询进程，将查询结果放到数据库中
    if data['query_id'] == -1: #第一次查询，启动查询进程
        query_id = round(time.time())
        p = mp.Process(target=search_proc, args=(data, logger))
        p.daemon = True
        p.start()
        proc_pool[query_id] = p
    else:
        sql = "select `cluster_id`, `face_image_uri`, `similarity` from `t_search` where `query_id` = %s  order by `similarity` desc limit %s,%s"
        result = db.select(sql, (data['query_id'], data['start_pos'], data['limit']))
        for item in result:
            pass
            # todo return search result



@search.route('/status', methods=['GET'])
def status1():
    '''
    人脸搜索异步返回的状态
    :return:
    '''
    start = time.time()



