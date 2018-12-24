import configparser
import json
import os
import sys
import time
from multiprocessing import Process

from flask import Blueprint, request

# get current file dir

sup = os.path.dirname(os.path.realpath(__file__))
sup = os.path.dirname(sup)
if sup not in sys.path:
    sys.path.append(sup)

from .error import *
from .param_tool import check_param, update_param, check_date
from util import Log, time_to_date
from util import Mysql
from util import trans_sqlin, trans_sqlinsert

logger = Log('peer', 'logs/')
config = configparser.ConfigParser()
config.read('./app.config')

db = Mysql(host=config.get('db', 'host'),
           port=config.getint('db', 'port'),
           user=config.get('db', 'user'),
           password=config.get('db', 'password'),
           db=config.get('db', 'db'),
           charset=config.get('db', 'charset'))
db.set_logger(logger)

bp_peer = Blueprint('peer', __name__)
proc_pool = {}


def compute(data, logger, query_id):
    '''
    同行人计算的进程，异步查询结果，将结果写入数据库
    :param data:
    :param logger:
    :return:
    '''
    # 1. 计算目标cluster的时间和摄像头
    if data['camera_ids'] != 'all':
        sql = "select `timestamp`, `camera_id`, `uri` from `t_cluster` where `cluster_id` = %s and `timestamp` between %s and %s and `camera_id` in {}".format(
            trans_sqlin(data['camera_ids']))
    else:
        sql = "select `timestamp`, `camera_id`, `uri` from `t_cluster` where `cluster_id` = %s and `timestamp` between %s and %s "
    select_result = db.select(sql, (data['cluster_id'], data['start'], data['end']))
    if select_result is None or len(select_result) == 0:
        logger.info('select from t_cluster error or result is null')
        logger.info('peer compute process interrupt')
        return
    else:
        logger.info('select from t_cluster success')
        timestamps = list(map(lambda x: x[0], select_result))
        camera_ids = list(map(lambda x: x[1], select_result))
        src_imgs = list(map(lambda x: x[2], select_result))

        # 同行人算法
        peers_cluster_ids = []  # 在t_k 前后gap内，在C_k摄像头下面出现的cluster的集合的list, 二维数组，下同
        peers_timestamps = []
        peers_uris = []
        for i, t in enumerate(timestamps):
            sql = "select `cluster_id`,`timestamp`,`uri` from `t_cluster` where `timestamp` between %s and %s and `camera_id` = %s"
            t1 = time_to_date(t.timestamp() - data['gap'])
            t2 = time_to_date(t.timestamp() + data['gap'])
            result = db.select(sql, (t1, t2, camera_ids[i]))
            temp_cluster = list(map(lambda x: x[0], result))
            temp_time = list(map(lambda x: x[1], result))
            temp_uri = list(map(lambda x: x[2], result))
            peers_cluster_ids.append(temp_cluster)
            logger.info('temp_timestamp: ', temp_time)
            peers_timestamps.append(temp_time)
            peers_uris.append(temp_uri)

        # 过滤掉重复的候选的cluster_ids
        candidate_cids = set()
        set(map(lambda x: candidate_cids.update(x), peers_cluster_ids))
        peer_infos = []
        for cluster_id in candidate_cids:
            # 统计每个cluster的具体信息, 轨迹向量，轨迹图片，轨迹时间
            trace_vector = []  # 候选cluster的轨迹向量
            trace_img = []
            trace_timestamp = []
            for j, peer_cluster in enumerate(peers_cluster_ids):
                if cluster_id in peer_cluster:
                    trace_vector.append(1)
                    trace_img.append(peers_uris[j][0])
                    trace_timestamp.append(peers_timestamps[j][0])
                else:
                    trace_vector.append(0)
                    trace_img.append('null')
                    trace_timestamp.append('null')

            prob = round(sum(trace_vector) / len(peers_cluster_ids), 3)
            logger.info('trace_vector: ', trace_vector)
            if prob < data['threshold']:
                logger.info('[cluster_id = %s] peer prob = %f , less than threshold' % (cluster_id, prob))
                # candidate_cids.remove(cluster_id)
                continue
            else:
                logger.info('[cluster_id = %s] peer prob = %f , more than threshold' % (cluster_id, prob))
                peer_info = {'cluster_id': cluster_id, 'times': sum(trace_vector),
                             'start_time': peers_timestamps[trace_vector.index(1)][0],
                             'end_time': peers_timestamps[trace_vector[::-1].index(1)][-1], 'prob': prob}
                peer_details = []
                for i, v in enumerate(trace_vector):
                    if v == 1:  # 代表和目标相遇
                        peer_detail = {'src_img': src_imgs[i], 'peer_img': trace_img[i], 'src_time': timestamps[i],
                                       'peer_time': trace_timestamp[i], 'camera_id': camera_ids[i]}
                        peer_details.append(peer_detail)
                peer_info['detail'] = peer_details
                peer_infos.append(peer_info)
        total = len(peer_infos)  # total条数
        # 写入t_peer 和 t_peer_detail数据库
        logger.info('peer_info total:', total)
        for peer_info in peer_infos:
            sql = "insert into `t_peer`(`query_id`, `total`, `cluster_id`, `times`, `start_time`, `end_time`, `prob`)" \
                  "values {}".format(trans_sqlinsert([
                [query_id, total, peer_info['cluster_id'], peer_info['times'],
                 peer_info['start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                 peer_info['end_time'].strftime('%Y-%m-%d %H:%M:%S'), peer_info['prob']]]))
            logger.info('sql', sql)
            insert_result = db.insert(sql)
            if insert_result == -1:
                logger.info('insert to t_peer error, please check')
            else:
                logger.info('insert to t_peer successfully, t_peer.id = %d' % insert_result)
                db.commit()
                logger.info('start insert peer_detail to t_peer_detail')
                values = [[insert_result, x['src_img'], x['peer_img'], x['src_time'].strftime('%Y-%m-%d %H:%M:%S'),
                           x['peer_time'].strftime('%Y-%m-%d %H:%M:%S'), x['camera_id']] for x in peer_info['detail']]
                sql = "insert into `t_peer_detail` values {}".format(trans_sqlinsert(values))
                detail_insert_result = db.insert(sql)
                if detail_insert_result == -1:
                    logger.info('insert to t_peer_detail error, please check')
                else:
                    logger.info('insert to t_peer_detail successfully')
                    db.commit()
    logger.info('peer compute process(%d) has done' % os.getpid())


@bp_peer.route('/peer', methods=['POST'])
def peer():
    '''
    查询同行人
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    necessary_params = {'cluster_id', 'start', 'end', 'gap', 'min_times', 'threshold', 'start_pos', 'limit'}
    default_params = {'query_id': -1, 'camera_ids': 'all'}
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
    # check start end 格式问题
    b_date = check_date(data['start'], data['end'])
    if not b_date:
        logger.warning(TRACE_ERR['time_format_err'])
        ret['message'] = TRACE_ERR['time_format_err']
        return json.dumps(ret)
    data = update_param(default_params, data)
    logger.info('parameters:', data)

    # 1. 启动查询进程，查询结果放到数据库中
    if data['query_id'] == -1:
        query_id = round(time.time())
        p = Process(target=compute, args=(data, logger, query_id))
        p.daemon = True
        p.start()
        proc_pool[query_id] = p
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['rtn'] = 0
        ret['query_id'] = query_id
        logger.info('启动peer compute 进程, process_key: ', query_id)
    else:
        # 2. 第二次查询，直接查表
        tmp = db.select("select count(*) from t_peer where query_id = %s", data['query_id'])
        if data['query_id'] not in proc_pool and (tmp is None or tmp[0][0] == 0):
            logger.info('query task %s 不存在' % data['query_id'])
            ret['rtn'] = -1
            ret['message'] = PEER_ERR['query_not_exist']
        elif data['query_id'] in proc_pool and proc_pool[data['query_id']].is_alive():
            logger.info('query task 正在进行中')
            ret['rtn'] = -2
            ret['message'] = PEER_ERR['query_in_progress']
            ret['status'] = PEER_ERR['doing']
        else:
            logger.info('query task 已经执行完毕')
            sql = "select x.cluster_id, c.uri, x.times, x.start_time, x.end_time, x.prob, d.src_img, d.peer_img, d.src_time, d.peer_time, d.camera_id " \
                  "from (select p.query_id, p.id, p.cluster_id, p.times, p.start_time, p.end_time, p.prob from t_peer p where query_id = %s order by p.prob limit %s, %s) x " \
                  "left join t_peer_detail d on x.id = d.id " \
                  "inner join (" \
                  "select a.cluster_id, a.uri from t_cluster a inner join " \
                  "(select cluster_id, max(`timestamp`) `anchor_time` from t_cluster group by cluster_id) b " \
                  "on a.cluster_id = b.cluster_id and a.timestamp = b.anchor_time group by a.cluster_id) c where c.cluster_id = x.cluster_id"
            select_result = db.select(sql, (data['query_id'], data['start_pos'], data['limit']))
            if select_result is None or len(select_result) == 0:
                logger.info('select from t_peer error or result is null')
                ret['rtn'] = -1
                ret['query_id'] = data['query_id']
                ret['message'] = PEER_ERR['fail']
            else:
                logger.info('select from t_peer success')
                ret['rtn'] = 0
                ret['query_id'] = data['query_id']
                clusters = set(map(lambda x:x[0], select_result))
                ret['total'] = len(clusters)
                ret['message'] = PEER_ERR['success']
                ret['status'] = PEER_ERR['done']

                results = []
                info = {}
                for item in select_result:
                    base_info = (item[0], item[1], item[2], item[3], item[4], item[5])
                    if base_info not in info:
                        info[base_info] = [(item[6],item[7],item[8],item[9],item[10])]
                    else:
                        info[base_info].append((item[6],item[7],item[8],item[9],item[10]))

                for k,v in info.items():
                    result = {'cluster_id': k[0], 'anchor_img': k[1], 'times': k[2],
                              'start_time': k[3].strftime('%Y-%m-%d %H:%M:%S'),
                              'end_time': k[4].strftime('%Y-%m-%d %H:%M:%S'), 'prob': k[5]}
                    details = []
                    for item in v:
                        detail = {'src_img': item[0], 'peer_img': item[1],
                                  'src_time': item[2].strftime('%Y-%m-%d %H:%M:%S'),
                                  'peer_time': item[3].strftime('%Y-%m-%d %H:%M:%S'),
                                  'camera_id': item[4]}
                        details.append(detail)
                    result['detail'] = details
                    results.append(result)
                ret['results'] = results
                ret['time_used'] = round((time.time() - start) * 1000)
    logger.info('peer api return: ', ret)
    return json.dumps(ret)
