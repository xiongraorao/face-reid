import configparser
import json
import multiprocessing as mp
import time

from flask import Blueprint, request

from rest.error import *
from rest.http_util import check_param, update_param
from util.face import Face
from util.logger import Log
from util.mysql import Mysql
from util.search import Faiss

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
threshold = 0.75 # 用于过滤找到的topk人脸

def search_proc(data, logger):
    '''
    查询进程，异步查询结果，将结果写入数据库
    :param data:
    :param logger:
    :return:
    '''
    # 1. 从索引接口中查询数据
    searcher = Faiss(config.get('api', 'faiss_host'), config.getint('api', 'faiss_port'))
    face_tool = Face(config.get('api', 'face_server'))
    detect_result = face_tool.detect(data['image_base64'])
    if detect_result['error_message'] == 601:
        logger.info('face detect successfully')
        # 提取特征
        left = detect_result['detect'][0]['left']
        top = detect_result['detect'][0]['top']
        width = detect_result['detect'][0]['width']
        height = detect_result['detect'][0]['height']
        cropped_face = face_tool.crop(left, top, width, height, data['image_base64'], b64=True)
        feature = face_tool.extract(cropped_face, detect_result['detect'][0]['landmark'])
        search_result = searcher.search(1, data['topk'] * 100, [feature])
        if search_result['rtn'] == 0:
            logger.info('search successfully')

            # 过滤掉低于给定阈值相似度的向量
            sample_ids = []
            for i, distance in enumerate(search_result['results']['distances'][0]):
                if distance > threshold:
                    sample_ids.append(search_result['results']['labels'][0][i])
            logger.info('real topk is:', len(sample_ids))
            # todo 结合camera_ids的限制条件， t_cluster查询到cluster的id，然后返回出去

    if data['camera_ids'] == 'all':
        # 查询所有摄像头
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
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['rtn'] = 0
        ret['message'] = SEARCH_ERR['start']
        ret['query_id'] = query_id
        logger.info('启动search进程, process_key: ', query_id)
    else:
        sql = "select `cluster_id`, `face_image_uri`, `similarity` from `t_search` where `query_id` = %s  order by `similarity` desc limit %s,%s"
        result = db.select(sql, (data['query_id'], data['start_pos'], data['limit']))
        if result is None:
            logger.info('mysql db select error, please check')
            ret['rtn'] = -1
            ret['query_id'] = data['query_id']
            ret['message'] = SEARCH_ERR['fail']
        else:
            logger.info('search success, length =', len(result))
            ret['rtn'] = 0
            ret['query_id'] = data['query_id']
            ret['total'] = len(result)
            results = []
            for item in result:
                sql = "select t_contact.person_id, t_contact.repository_id t_lib.name from t_contact left join t_lib" \
                      " on t_contact.reposity_id = t_lib.repository_id where t_contact.cluster_id = %s"
                tmp_res = db.select(sql, (item[0]))
                tmp = {'cluster_id': item[0], 'face_image_uri': item[1], 'similarity': item[2]}
                if tmp_res is not None and len(tmp_res) > 0:
                    logger.info('找到 cluster_id =', item[0], '所匹配的人像库信息')
                    tmp['reposity_info'] = {'person_id': tmp_res[0][0], 'repository_id': tmp_res[0][1],
                                            'name': tmp_res[0][2]}
                results.append(tmp)
            ret['results'] = results
            ret['time_used'] = round((time.time() - start) * 1000)
    logger.info('search api return: ', ret)
    return json.dumps(ret)


@search.route('/libs', methods=['POST'])
def search2():
    '''
    人脸搜索，静态库检索
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    necessary_params = {'repository_ids', 'start_pos', 'limit'}
    default_params = {'query_id': -1, 'camera_ids': 'all', 'topk': 100}
    ret = {'time_used': 0, 'rtn': -1, 'query_id': -1}
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

@search.route('/status', methods=['GET'])
def status1():
    '''
    人脸搜索异步返回的状态
    :return:
    '''
    start = time.time()




