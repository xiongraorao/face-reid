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
from util import Face, trans_sqlin, trans_sqlinsert
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
bp_search = Blueprint('search', __name__)

lib_searcher = Faiss(config.get('api', 'faiss_lib_host'), config.getint('api', 'faiss_lib_port'))
face_tool = Face(config.get('api', 'face_server'))

proc_pool = {}
threshold = 0.75 # 用于过滤找到的topk人脸


def search_proc(data, query_id):
    '''
    查询进程，异步查询结果，将结果写入数据库
    :param data:
    :param logger:
    :return:
    '''
    # 1. 从索引接口中查询数据
    start = time.time()
    logger = Log('search-process', 'logs/')
    logger.info('========================%s start ===================='%os.getpid())
    logger.info('start search process, pid = %s' % os.getpid())
    searcher = Faiss(config.get('api', 'faiss_host'), config.getint('api', 'faiss_port'))
    tool = Face(config.get('api', 'face_server'))
    feature = tool.feature(data['image_base64'])
    if feature is not None:
        logger.info('face feature extracted successfully')
        search_result = searcher.search(1, data['topk'] * 100, [feature]) # 这里默认平均每个cluster大小为100，这样的话，找出来的cluster的个数可能就接近topk
        if search_result['rtn'] == 0:
            logger.info('search successfully')
            dist_lable = list(map(lambda x, y: (x, y), search_result['results']['distances'][0],
                                  search_result['results']['lables'][0]))
            # 过滤掉低于给定阈值相似度的向量
            dist_lable = list(filter(lambda x: x[0] > threshold, dist_lable))
            distances = list(map(lambda x: x[0], dist_lable))
            lables = list(map(lambda x: x[1], dist_lable))
            logger.info('real topk is:', len(lables))
            if data['camera_ids'] == 'all':
                sql = "select `cluster_id` from t_cluster where id in {} order by field (id, {}) " \
                    .format(trans_sqlin(lables), trans_sqlin(lables)[1:-1])
            else:
                sql = "select `cluster_id` from t_cluster where id in {} and `camera_id` in {} order by field (id, {}) " \
                    .format(trans_sqlin(lables), trans_sqlin(data['camera_ids']), trans_sqlin(lables)[1:-1])
            select_result = db.select(sql)
            if select_result is not None and len(select_result) > 0:
                logger.info('select from t_cluster success')
                clusters = list(map(lambda x: x[0], select_result))
                assert len(clusters) == len(distances), 'cluster select error'

                # 统计属于哪个cluster
                cluster_dic = {}  # cluster-> [distance1, distance2...]
                for j in range(len(clusters)):
                    if clusters[j] not in cluster_dic:
                        cluster_dic[clusters[j]] = [distances[j]]
                    else:
                        cluster_dic[clusters[j]].append(distances[j])
                for k, v in cluster_dic.items():
                    cluster_dic[k] = sum(v) / len(v)  # 每个cluster和目标对应的平均相似度
                # 按照value的值从大到小排序
                cluster_sims = sorted(list(cluster_dic.items()), key=lambda x: x[1], reverse=True)
                values = tuple(map(lambda x, y: (x[0], x[1], y), cluster_sims, [query_id] * len(cluster_sims)))
                logger.info('values: ', values)
                sql = "insert into `t_search` (`cluster_id`, `similarity`, `query_id`) values {} ".format(
                    trans_sqlinsert(values))
                insert_result = db.insert(sql)
                if insert_result != -1:
                    db.commit()
                    logger.info('insert to t_search success')
                else:
                    logger.error('insert to t_search failed')
            else:
                logger.error('select from t_cluster failed or result is null')
        else:
            logger.error('faiss searcher service error, error message: ', search_result['message'])
    else:
        logger.error('verifier service error')
    time_used = round(time.time() - start)
    logger.info('search process(%d) have done, cost time = %d s ' % (os.getpid(), time_used))
    logger.info('========================%s start ===================='%os.getpid())

@bp_search.route('/all', methods=['POST'])
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
    logger.info('parameters:', str(data)[:100])

    # 1. 启动查询进程，将查询结果放到数据库中
    if data['query_id'] == -1: #第一次查询，启动查询进程
        query_id = round(time.time())
        p = mp.Process(target=search_proc, args=(data, query_id))
        p.daemon = True
        p.start()
        proc_pool[query_id] = p
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['rtn'] = 0
        ret['message'] = SEARCH_ERR['start']
        ret['query_id'] = query_id
        logger.info('启动search进程, process_key(query_id): ', query_id)
    else:
        # 2. 第二次查询
        tmp = db.select("select count(*) from t_search where query_id = %s", data['query_id'])
        if data['query_id'] not in proc_pool and (tmp is None or tmp[0][0] == 0) :
            logger.info('query task %s 不存在'% data['query_id'])
            ret['rtn'] = -2
            ret['message'] = SEARCH_ERR['query_not_exist']
        elif data['query_id'] in proc_pool and proc_pool[data['query_id']].is_alive():
            logger.info('query task 正在进行中')
            ret['rtn'] = -2
            ret['message'] = SEARCH_ERR['query_in_progress']
            ret['status'] = SEARCH_ERR['doing']
        else:
            logger.info('query task 已经执行完毕')
            sql = "select e.cluster_id, e.anchor, e.similarity, f.person_id, f.repository_id, f.repo_name from" \
                  "(select x.cluster_id, x.similarity , y.anchor from (select cluster_id, similarity from t_search where query_id = %s order by `similarity` desc limit %s,%s ) " \
                  "x left join" \
                  "(select a.cluster_id, a.uri anchor from t_cluster a inner join (select cluster_id, max(`timestamp`) `anchor_time` from t_cluster " \
                  "group by cluster_id) b on a.cluster_id = b.cluster_id and a.timestamp = b.anchor_time group by a.cluster_id ) y on x.cluster_id = y.cluster_id) e left join " \
                  "(select c.id, c.name person_id, c.cluster_id, c.repository_id, d.name repo_name from " \
                  "(select a.id,a.cluster_id, b.name, b.repository_id from (select id,cluster_id from t_contact) a left join t_person b on a.id = b.id ) c " \
                  "left join t_lib d on c.repository_id = d.repository_id) f on e.cluster_id = f.cluster_id"
            select_result = db.select(sql, (data['query_id'], data['start_pos'], data['limit']))
            if select_result is None or len(select_result) == 0:
                logger.info('mysql db select error, please check')
                ret['rtn'] = -1
                ret['query_id'] = data['query_id']
                ret['message'] = SEARCH_ERR['null']
            else:
                logger.info('search success, length =', len(select_result))
                ret['rtn'] = 0
                ret['query_id'] = data['query_id']
                clusters = set(map(lambda x:x[0], select_result))
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
                for k,v in info.items():
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
    return json.dumps(ret)


@bp_search.route('/repos', methods=['POST'])
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
    sql = "select x.*, y.name repo_name from (" \
          "select  e.cluster_id, e.similarity, f.anchor, e.person_id, e.repository_id from (select c.id, c.name person_id, c.repository_id, d.cluster_id, d.similarity from (select id, name, repository_id from t_person where repository_id in {}) c" \
          "left join t_contact d on c.id = d.id order by d.similarity desc) e  left join " \
          "(select a.cluster_id, a.uri anchor from t_cluster a inner join (select cluster_id, max(`timestamp`) `anchor_time` from t_cluster " \
          "group by cluster_id) b on a.cluster_id = b.cluster_id and a.timestamp = b.anchor_time group by a.cluster_id) f on e.cluster_id = f.cluster_id ) x left join" \
          "t_lib y on x.repository_id = y.repository_id".format(trans_sqlin(repository_ids))

    select_result = db.select(sql)
    if select_result is not None and len(select_result) > 0:
        logger.info('select success, cluster size: ', len(select_result))
        results = []
        for item in select_result:
            result = {'cluster_id': item[0], 'anchor_img': item[1], 'similarity': item[2], 'repository_info': {'person_id': item[3], 'repository_id': item[4], 'name': item[5]}}
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
        ret['rtn'] = -1
        ret['query_id'] = -1
    logger.info('search2 api return: ', ret)
    return json.dumps(ret)


@bp_search.route('/libs', methods=['POST'])
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

    feature = face_tool.feature(data['image_base64'])
    search_result = lib_searcher.search(1, data['topk'] * 100, [feature])
    if search_result['rtn'] == 0:
        logger.info('search successfully')
        dist_lable = list(map(lambda x, y: (x, y), search_result['results']['distances'][0],
                              search_result['results']['lables'][0]))
        # 过滤掉低于给定阈值相似度的向量
        dist_lable = list(filter(lambda x: x[0] > threshold, dist_lable))
        distances = list(map(lambda x: x[0], dist_lable))
        lables = list(map(lambda x: x[1], dist_lable))
        logger.info('real topk is:', len(lables))

        sql = "select g.cluster_id,g.anchor, g.similarity , g.name person_id, g.repository_id, h.name repo_name from (" \
              "select e.* , f.name, f.repository_id from " \
              "(select c.id, c.cluster_id,c.similarity, d.anchor from " \
              "(select a.id, b.cluster_id, b.similarity from " \
              "(select id from t_person where id in {} ) a " \
              "left join t_contact b on a.id = b.id) c " \
              "left join (select a.cluster_id, a.uri anchor from t_cluster a " \
              "inner join (select cluster_id, max(`timestamp`) `anchor_time` from " \
              "t_cluster group by cluster_id) b on a.cluster_id = b.cluster_id and a.timestamp = b.anchor_time group by a.cluster_id ) d on c.cluster_id = d.cluster_id) e " \
              "left join t_person f on e.id = f.id) g " \
              "left join t_lib h on g.repository_id = h.repository_id order by g.similarity desc".format(
            trans_sqlin(lables))
        select_result = db.select(sql)
        if select_result is None or len(select_result) == 0:
            logger.info('select from t_cluster failed or result is null')
            ret['rtn'] = -1
        else:
            logger.info('select from t_cluster success, cluster size: ', len(select_result))
            results = []
            for item in select_result:
                result = {'cluster_id': item[0], 'anchor_img': item[1], 'similarity': item[2],
                          'repository_info': {'person_id': item[3], 'repository_id': item[4], 'name': item[5]}}
                results.append(result)
            ret['rtn'] = 0
            clusters = set(map(lambda x:x[0], select_result))
            ret['total'] = len(clusters)
            ret['message'] = SEARCH_ERR['success']
            ret['time_used'] = round((time.time() - start) * 1000)
            ret['total'] = len(select_result)
            ret['results'] = results
    else:
        logger.info('search failed! please check faiss_lib_search service')
        ret['message'] = SEARCH_ERR['fail']
        ret['query_id'] = -1
    logger.info('search2 api return: ', ret)
    return json.dumps(ret)

