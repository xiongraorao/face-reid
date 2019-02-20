import configparser
import json
import multiprocessing as mp
import os
import sys
import time
import uuid

from flask import Blueprint, request

# get current file dir
sup = os.path.dirname(os.path.realpath(__file__))
sup = os.path.dirname(sup)
if sup not in sys.path:
    sys.path.append(sup)

from .error import *
from .param_tool import check_param_key, update_param
from util import Face
from util import Log
from util import Faiss
from util import trans_sqlin, get_db_client
from .proc_funcs import search_proc

logger = Log('search', 'logs/')
config = configparser.ConfigParser()
config.read('./app.config')
bp_search = Blueprint('search', __name__)
lib_searcher = Faiss(config.get('api', 'faiss_lib_host'), config.getint('api', 'faiss_lib_port'))
face_tool = Face(config.get('api', 'face_server'))
proc_pool = {}
threshold = 0.75  # 用于过滤找到的topk人脸
process_pool = mp.Pool(processes=20)


@bp_search.route('/all/syn', methods=['POST'])
def searchsyn():
    '''
    人脸搜索，动态库检索
    :return:
    '''
    start = time.time()
    db = get_db_client(config, logger)
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

    legal = check_param_key(set(data), necessary_params, set(default_params))
    if not legal:
        logger.warning(GLOBAL_ERR['param_err'])
        ret['message'] = GLOBAL_ERR['param_err']
        return json.dumps(ret)
    data = update_param(default_params, data)

    data['query_id'] = int(str(hash(uuid.uuid4()))[:9])
    search_proc(data, query_id=data['query_id'], config=config)
    logger.info('query task 已经执行完毕')

    sql = '''
    select e.cluster_id, e.anchor, e.similarity, f.person_id, f.repository_id, f.repo_name from
    (select x.cluster_id, x.similarity , y.anchor from (select cluster_id, similarity from t_search where query_id = %s order by `similarity` desc limit %s,%s ) 
    x left join
    (select a.cluster_id, a.uri anchor from t_cluster a inner join (select cluster_id, max(`timestamp`) `anchor_time` from t_cluster 
    group by cluster_id) b on a.cluster_id = b.cluster_id and a.timestamp = b.anchor_time group by a.cluster_id ) y on x.cluster_id = y.cluster_id) e left join 
    (select c.id, c.name person_id, c.cluster_id, c.repository_id, d.name repo_name from 
    (select a.id,a.cluster_id, b.name, b.repository_id from (select id,cluster_id from t_contact) a left join t_person b on a.id = b.id ) c 
    left join t_lib d on c.repository_id = d.repository_id) f on e.cluster_id = f.cluster_id
    '''
    select_result = db.select(sql, (data['query_id'], data['start_pos'], data['limit']))
    if select_result is None or len(select_result) == 0:
        logger.info('mysql db select error, please check')
        ret['rtn'] = -2
        ret['query_id'] = data['query_id']
        ret['message'] = SEARCH_ERR['null']
    else:
        logger.info('search success, length =', len(select_result))
        ret['rtn'] = 0
        ret['query_id'] = data['query_id']
        clusters = set(map(lambda x: x[0], select_result))
        ret['total'] = len(clusters)
        ret['message'] = SEARCH_ERR['success']
        ret['status'] = SEARCH_ERR['done']

        results = []
        info = {}
        for item in select_result:
            base_info = (item[0], item[1], item[2])
            if base_info not in info:
                info[base_info] = [(item[3], item[4], item[5])]
            else:
                info[base_info].append((item[3], item[4], item[5]))
        for k, v in info.items():
            result = {'cluster_id': k[0], 'anchor_img': k[1], 'similarity': k[2]}
            repo_infos = []
            for i in v:
                repo_info = {'person_id': i[0], 'repository_id': i[1], 'name': i[2]}
                repo_infos.append(repo_info)
            result['repository_infos'] = repo_infos
            results.append(result)
        ret['results'] = results
        ret['time_used'] = round((time.time() - start) * 1000)

    logger.info('search1 api return: ', ret)
    db.close()
    return json.dumps(ret)


@bp_search.route('/all', methods=['POST'])
def search():
    '''
    人脸搜索，动态库检索
    :return:
    '''
    start = time.time()
    db = get_db_client(config, logger)
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

    legal = check_param_key(set(data), necessary_params, set(default_params))
    if not legal:
        logger.warning(GLOBAL_ERR['param_err'])
        ret['message'] = GLOBAL_ERR['param_err']
        return json.dumps(ret)
    data = update_param(default_params, data)

    # 1. 启动查询进程，将查询结果放到数据库中
    if data['query_id'] == -1:  # 第一次查询，启动查询进程
        query_id = int(str(hash(uuid.uuid4()))[:9])
        process_pool.apply_async(search_proc, (data, query_id, config))
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['rtn'] = 0
        ret['message'] = SEARCH_ERR['start']
        ret['query_id'] = query_id
        logger.info('启动search进程, process_key(query_id): ', query_id)
    else:
        # 2. 第二次查询
        tmp = db.select("select count(*) from t_search where query_id = %s", data['query_id'])
        if tmp is None or tmp[0][0] == 0:
            logger.info('query task %s 不存在或运行中' % data['query_id'])
            ret['rtn'] = -3
            ret['message'] = SEARCH_ERR['query_not_exist']
        else:
            logger.info('query task 已经执行完毕')
            sql = '''
            select e.cluster_id, e.anchor, e.similarity, f.person_id, f.repository_id, f.repo_name from
            (select x.cluster_id, x.similarity , y.anchor from (select cluster_id, similarity from t_search where query_id = %s order by `similarity` desc limit %s,%s ) 
            x left join
            (select a.cluster_id, a.uri anchor from t_cluster a inner join (select cluster_id, max(`timestamp`) `anchor_time` from t_cluster 
            group by cluster_id) b on a.cluster_id = b.cluster_id and a.timestamp = b.anchor_time group by a.cluster_id ) y on x.cluster_id = y.cluster_id) e left join 
            (select c.id, c.name person_id, c.cluster_id, c.repository_id, d.name repo_name from 
            (select a.id,a.cluster_id, b.name, b.repository_id from (select id,cluster_id from t_contact) a left join t_person b on a.id = b.id ) c 
            left join t_lib d on c.repository_id = d.repository_id) f on e.cluster_id = f.cluster_id
            '''
            select_result = db.select(sql, (data['query_id'], data['start_pos'], data['limit']))
            if select_result is None or len(select_result) == 0:
                logger.info('mysql db select error, please check')
                ret['rtn'] = -2
                ret['query_id'] = data['query_id']
                ret['message'] = SEARCH_ERR['null']
            else:
                logger.info('search success, length =', len(select_result))
                ret['rtn'] = 0
                ret['query_id'] = data['query_id']
                clusters = set(map(lambda x: x[0], select_result))
                ret['total'] = len(clusters)
                ret['message'] = SEARCH_ERR['success']
                ret['status'] = SEARCH_ERR['done']

                results = []
                info = {}
                for item in select_result:
                    base_info = (item[0], item[1], item[2])
                    if base_info not in info:
                        info[base_info] = [(item[3], item[4], item[5])]
                    else:
                        info[base_info].append((item[3], item[4], item[5]))
                for k, v in info.items():
                    result = {'cluster_id': k[0], 'anchor_img': k[1], 'similarity': k[2]}
                    repo_infos = []
                    for i in v:
                        repo_info = {'person_id': i[0], 'repository_id': i[1], 'name': i[2]}
                        repo_infos.append(repo_info)
                    result['repository_infos'] = repo_infos
                    results.append(result)
                ret['results'] = results
                ret['time_used'] = round((time.time() - start) * 1000)
    logger.info('search1 api return: ', ret)
    db.close()
    return json.dumps(ret)


@bp_search.route('/repos', methods=['POST'])
def search2():
    '''
    人脸搜索，静态库检索, 直接查找静态表
    :return:
    '''
    start = time.time()
    db = get_db_client(config, logger)
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

    legal = check_param_key(set(data), necessary_params, set(default_params))
    if not legal:
        logger.warning(GLOBAL_ERR['param_err'])
        ret['message'] = GLOBAL_ERR['param_err']
        return json.dumps(ret)
    data = update_param(default_params, data)

    repository_ids = data['repository_ids']
    sql = '''
    select x.*, y.name repo_name from (
    select  e.cluster_id, e.similarity, f.anchor, e.person_id, e.repository_id from (
    select c.id, c.name person_id, c.repository_id, d.cluster_id, d.similarity from (
    select id, name, repository_id from t_person where repository_id in {} limit {},{}) c
    left join t_contact d on c.id = d.id order by d.similarity desc) e  left join 
    (select a.cluster_id, a.uri anchor from t_cluster a inner join (select cluster_id, max(`timestamp`) `anchor_time` from t_cluster 
    group by cluster_id) b on a.cluster_id = b.cluster_id and a.timestamp = b.anchor_time group by a.cluster_id) f on e.cluster_id = f.cluster_id ) x left join
    t_lib y on x.repository_id = y.repository_id
    '''.format(trans_sqlin(repository_ids), data['start_pos'], data['limit'])

    select_result = db.select(sql)
    if select_result is not None and len(select_result) > 0:
        logger.info('select success, cluster size: ', len(select_result))
        results = []
        for item in select_result:
            result = {'cluster_id': item[0], 'anchor_img': item[1], 'similarity': item[2],
                      'repository_info': {'person_id': item[3], 'repository_id': item[4], 'name': item[5]}}
            results.append(result)
        ret['rtn'] = 0
        ret['message'] = SEARCH_ERR['success']
        ret['query_id'] = -1
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['total'] = len(select_result)
        ret['results'] = results
    else:
        logger.info('repository is null or mysql db select error')
        ret['message'] = SEARCH_ERR['null']
        ret['rtn'] = -2
    logger.info('search2 api return: ', ret)
    db.close()
    return json.dumps(ret)


@bp_search.route('/libs', methods=['POST'])
def search3():
    '''
    在静态库中索引，然后关联到动态库，返回结果
    :return:
    '''
    start = time.time()
    db = get_db_client(config, logger)
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

    legal = check_param_key(set(data), necessary_params, set(default_params))
    if not legal:
        logger.warning(GLOBAL_ERR['param_err'])
        ret['message'] = GLOBAL_ERR['param_err']
        return json.dumps(ret)
    data = update_param(default_params, data)

    feature = face_tool.feature(data['image_base64'])
    search_result = lib_searcher.search(1, data['topk'] * 100, [feature])
    if search_result is not None and search_result['rtn'] == 0:
        logger.info('search successfully')
        dist_lable = list(map(lambda x, y: (x, y), search_result['results']['distances'][0],
                              search_result['results']['lables'][0]))
        # 过滤掉低于给定阈值相似度的向量
        dist_lable = list(filter(lambda x: x[0] > threshold, dist_lable))
        distances = list(map(lambda x: x[0], dist_lable))
        lables = list(map(lambda x: x[1], dist_lable))
        logger.info('real topk is:', len(lables))

        sql = '''
        select g.cluster_id, g.anchor, g.similarity, g.name person_id, g.repository_id, h.name repo_name from (
        select e.* , f.name, f.repository_id from 
        (select c.id, c.cluster_id,c.similarity, d.anchor from 
        (select a.id, b.cluster_id, b.similarity from 
        (select id from t_person where id in {} limit {},{} ) a 
        left join t_contact b on a.id = b.id) c 
        left join (select a.cluster_id, a.uri anchor from t_cluster a 
        inner join (select cluster_id, max(`timestamp`) `anchor_time` from 
        t_cluster group by cluster_id) b on a.cluster_id = b.cluster_id and a.timestamp = b.anchor_time group by a.cluster_id ) d 
        on c.cluster_id = d.cluster_id) e 
        left join t_person f on e.id = f.id) g 
        left join t_lib h on g.repository_id = h.repository_id order by g.similarity desc
        '''.format(trans_sqlin(lables), data['start_pos'], data['limit'])

        select_result = db.select(sql)
        if select_result is None or len(select_result) == 0:
            logger.info('select from t_cluster failed or result is null')
            ret['rtn'] = -2
            ret['message'] = SEARCH_ERR['null']
        else:
            logger.info('select from t_cluster success, cluster size: ', len(select_result))
            results = []
            for item in select_result:
                result = {'cluster_id': item[0], 'anchor_img': item[1], 'similarity': item[2],
                          'repository_info': {'person_id': item[3], 'repository_id': item[4], 'name': item[5]}}
                results.append(result)
            ret['rtn'] = 0
            clusters = set(map(lambda x: x[0], select_result))
            ret['total'] = len(clusters)
            ret['message'] = SEARCH_ERR['success']
            ret['time_used'] = round((time.time() - start) * 1000)
            ret['total'] = len(select_result)
            ret['results'] = results
    else:
        logger.info('search failed! please check faiss_lib_search service')
        ret['rtn'] = -6
        ret['message'] = SEARCH_ERR['fail']
    logger.info('search3 api return: ', ret)
    db.close()
    return json.dumps(ret)
