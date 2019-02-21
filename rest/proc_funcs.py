# -*- coding: utf-8 -*-
"""

Created on 2019-02-20 20:35
@author Xiong Raorao

"""
import configparser
import os
import sys
import time

# get current file dir
sup = os.path.dirname(os.path.realpath(__file__))
sup = os.path.dirname(sup)
if sup not in sys.path:
    sys.path.append(sup)

from util import Face
from util import Log
from util import Faiss
from util import trans_sqlin, trans_sqlinsert, get_db_client

config = configparser.ConfigParser()
config.read('./app.config')
threshold = config.getfloat('sys', 'threshold')  # 用于过滤找到的topk人脸


def search_proc(data, query_id, config):
    '''
    查询进程，异步查询结果，将结果写入数据库
    :param data:
    :param logger:
    :return:
    '''
    # 1. 从索引接口中查询数据
    start = time.time()
    logger = Log('search-process', 'logs/')
    db = get_db_client(config, logger)
    logger.info('=====proc: %s start, query_id: %s =====' % (os.getpid(), query_id))
    logger.info('start search process, pid = %s' % os.getpid())
    searcher = Faiss(config.get('api', 'faiss_host'), config.getint('api', 'faiss_port'))
    tool = Face(config.get('api', 'face_server'))
    feature = tool.feature(data['image_base64'])
    if feature is not None:
        logger.info('face feature extracted successfully')
        search_result = searcher.search(1, data['topk'] * 100,
                                        [feature])  # 这里默认平均每个cluster大小为100，这样的话，找出来的cluster的个数可能就接近topk
        if search_result is not None and search_result['rtn'] == 0:
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
                return -3
        else:
            logger.error('faiss searcher service error, error message: ', search_result['message'])
            return -2
    else:
        logger.error('verifier service error')
        return -1
    time_used = round(time.time() - start)
    logger.info('search process(%d) have done, cost time = %d s ' % (os.getpid(), time_used))
    logger.info('=====proc: %s end, query_id: %s =====' % (os.getpid(), query_id))
    db.close()
    return 0
