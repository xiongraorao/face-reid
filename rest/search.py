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
from .param_tool import check_param, update_param
from util import Face
from util import Log
from util import Mysql
from util import Faiss

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

def search_proc(data, logger, query_id, start_time):
    '''
    查询进程，异步查询结果，将结果写入数据库
    :param data:
    :param logger:
    :return:
    '''
    # 1. 从索引接口中查询数据
    # todo 修改搜索的相似度计算问题
    searcher = Faiss(config.get('api', 'faiss_host'), config.getint('api', 'faiss_port'))
    face_tool = Face(config.get('api', 'face_server'))
    feature = face_tool.feature(data['image_base64'])
    if feature is not None:
        logger.info('face feature extracted successfully')
        search_result = searcher.search(1, data['topk'] * 100, [feature]) # 这里默认平均每个cluster大小为100，这样的话，找出来的cluster的个数可能就接近topk
        if search_result['rtn'] == 0:
            logger.info('search successfully')
            # 过滤掉低于给定阈值相似度的向量
            # sim_ids = [] # 存储相似的抓拍人脸id
            # sims = [] # 存储相似度的值
            sims = {} # 存储相似人脸的id和对应的相似度
            for i, distance in enumerate(search_result['results']['distances'][0]):
                if distance >= threshold:
                    sim_id = search_result['results']['labels'][0][i]
                    sims[sim_id] = distance
            logger.info('real topk is:', len(sims))
            # todo 结合camera_ids的限制条件， t_cluster查询到cluster的id，然后返回出去
            cluster_ids = []
            face_image_uris = []
            similarities = []
            if data['camera_ids'] == 'all':
                sql = "select `id`, `cluster_id`, `uri` from t_cluster where id in {} group by `cluster_id`".format(str(tuple(sims.keys())))
            else:
                sql = "select `id`, `cluster_id`, `uri` from t_cluster where `id` in {} and `camera_id` in {} group by `cluster_id`".format(str(tuple(sims.keys())), str(tuple(data['camera_ids'])))
            t_cluster_result = db.select(sql)
            if t_cluster_result is not None and len(t_cluster_result) > 0:
                logger.info('select from t_cluster success')
                temp_data = [ (x[1], x[2], sims[x[0]], query_id, start_time) for x in t_cluster_result ]
                sql = "insert into `t_search` (cluster_id, face_image_uri, similarity, query_id, time) values {} ".format(str(tuple(temp_data))[1:-1])
                insert_result = db.insert(sql)
                if insert_result != -1:
                    logger.info('insert to t_search success')
                else:
                    logger.error('insert to t_search failed')
            else:
                logger.error('select from t_cluster failed or result is null')
        else:
            logger.error('faiss searcher service error, error message: ', search_result['message'])
    else:
        logger.error('verifier service error')
    logger.info('search process(%d) have done ', os.getpid())


@search.route('/all', methods=['POST'])
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
        p = mp.Process(target=search_proc, args=(data, logger, query_id, query_id))
        p.daemon = True
        p.start()
        proc_pool[query_id] = p
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['rtn'] = 0
        ret['message'] = SEARCH_ERR['start']
        ret['query_id'] = query_id
        logger.info('启动search进程, process_key: ', query_id)
    else:
        # 2. 第二次查询
        if data['query_id'] not in proc_pool:
            logger.info('query task %s 不存在'% data['query_id'])
            ret['rtn'] = -2
            ret['message'] = SEARCH_ERR['query_not_exist']
        elif proc_pool[data['query_id']].is_alive():
            logger.info('query task 正在进行中')
            ret['rtn'] = -2
            ret['message'] = SEARCH_ERR['query_in_progress']
        else:
            logger.info('query task 已经执行完毕')
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
                    sql = "select x.id, t_person.repository_id t_lib.name from (select id from t_contact where cluster_id = %s) as x " \
                          "left join t_person " \
                          " on x.id = t_person.id left join t_lib on t_person.repository_id = t_lib.repository_id "

                    sql2 = "select t_contact.id , t_person.repository_id, t_lib.name from t_contact, t_perosn, t_lib " \
                           "where t_contact.cluster_id = %s and t_contact.id = t_person.id and t_person.repository_id = t_lib.repository_id"
                    tmp_res = db.select(sql, (item[0]))
                    tmp = {'cluster_id': item[0], 'face_image_uri': item[1], 'similarity': item[2]}
                    if tmp_res is not None and len(tmp_res) > 0:
                        logger.info('找到 cluster_id =', item[0], '所匹配的人像库信息')
                        repository_infos = []
                        for temp_item in tmp_res:
                            repository_infos.append({'person_id': temp_item[0], 'repository_id': temp_item[1],'name': temp_item[2]})
                        tmp['repository_infos'] = repository_infos
                    results.append(tmp)
                ret['results'] = results
                ret['time_used'] = round((time.time() - start) * 1000)
    logger.info('search1 api return: ', ret)
    return json.dumps(ret)


@search.route('/repos', methods=['POST'])
def search2():
    '''
    人脸搜索，静态库检索, 直接查找静态表
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

    # todo 直接查询`t_person` 和 `t_contact`
    repository_ids = data['repository_ids']
    sql = "select c.cluster_id, cl.uri, c.similarity, p.person_id, p.repository_id, lib.name from `t_person` as p where p.repository_id in {} limit {},{} " \
          "left join `t_contact` as c on p.id = c.id " \
          "left join `t_cluster` as cl on cl.cluster_id = c.cluser_id " \
          "left join `t_lib` as lib on lib.repository_id = p.repository_id".format(str(tuple(repository_ids)), data['start_pos'], data['limit'])

    sql = "select p.id, p.repository_id, lib.name, con.cluster_id, clu.uri from (t_person p " \
          "left join t_lib lib on p.repository_id = lib.repository_id where p.repository_id in {}) x " \
          "left join (t_contact con left join t_cluster clu on clu.cluster_id = con.cluster_id) y on x.id = y.id" \

    select_result = db.select(sql)
    results = []
    if select_result is not None and len(select_result) > 0:
        logger.info('select success, cluster size: ', len(select_result))
        # 根据cluster来读取对应的信息
        for item in select_result:
            tmp_result = {'cluster_id': item[0], 'face_image_uri': item[1], 'similarity': item[2]}
            info = {'person_id': item[3], 'repository_id': item[4], 'name': item[5]}
            tmp_result['repository_info'] = info
            results.append(tmp_result)
        ret['rtn'] = 0
        ret['message'] = SEARCH_ERR['success']
        ret['query_id'] = -1
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['total'] = len(select_result)
        ret['results'] = results
    else:
        logger.info('repository is null or `t_contact` is null')
        ret['message'] = SEARCH_ERR['null']
        ret['rtn'] = -1
    logger.info('search2 api return: ', ret)
    return json.dumps(ret)


@search.route('/libs', methods=['POST'])
def search3():
    '''
    在静态库中索引，然后关联到动态库，返回结果
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    necessary_params = {'image_base64', 'start_pos', 'limit'}
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

    face_tool = Face(config.get('api', 'face_server'))
    feature = face_tool.feature(data['image_base64'])
    searcher = Faiss(config.get('api', 'faiss_lib_host'), config.getint('api', 'faiss_lib_port'))
    search_result = searcher.search(1, data['topk'] * 100, [feature])
    if search_result['rtn'] == 0:
        logger.info('search successfully')
        # 过滤掉低于给定阈值相似度的向量
        # sim_ids = [] # 存储相似的抓拍人脸id
        # sims = [] # 存储相似度的值
        sims = {}  # 存储相似人脸的id和对应的相似度
        for i, distance in enumerate(search_result['results']['distances'][0]):
            if distance >= threshold:
                sim_id = search_result['results']['labels'][0][i]
                sims[sim_id] = distance
        logger.info('real topk is:', len(sims))
        sql = "select con.cluster_id, c.uri, con.similarity, p.person_id, p.respository_id, lib.name from t_person as p where p.id in {} " \
              "left join t_contact as con on p.id = con.id " \
              "left join t_cluster as c on c.cluster_id = con.cluster_id" \
              "left join t_lib as lib on p.repository_id = lib.repository_id".format(str(tuple(sims.keys())))
        select_result = db.select(sql)
        results = []
        if select_result is not None and len(select_result) > 0:
            logger.info('select success, cluster size: ', len(select_result))
            # 根据cluster来读取对应的信息
            for item in select_result:
                tmp_result = {'cluster_id': item[0], 'face_image_uri': item[1], 'similarity': item[2]}
                info = {'person_id': item[3], 'repository_id': item[4], 'name': item[5]}
                tmp_result['repository_info'] = info
                results.append(tmp_result)
            ret['rtn'] = 0
            ret['message'] = SEARCH_ERR['success']
            ret['query_id'] = -1
            ret['time_used'] = round((time.time() - start) * 1000)
            ret['total'] = len(select_result)
            ret['results'] = results
        else:
            logger.info('repository is null or `t_contact` is null')
            ret['message'] = SEARCH_ERR['null']
            ret['rtn'] = -1
    else:
        logger.info('search failed! please check faiss_lib_search service')
        ret['message'] = SEARCH_ERR['fail']
        ret['query_id'] = -1
    logger.info('search2 api return: ', ret)
    return json.dumps(ret)

