import configparser
import json
import os
import sys
import time

from flask import Blueprint, request
from multiprocessing import Process

# get current file dir
sup = os.path.dirname(os.path.realpath(__file__))
sup = os.path.dirname(sup)
if sup not in sys.path:
    sys.path.append(sup)

from .error import *
from .param_tool import check_param, update_param, check_date
from util import Log
from util import Mysql

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

peer = Blueprint('peer', __name__)
proc_pool = {}

def compute(data, logger, query_id, start_time):
    '''
    同行人计算的进程，异步查询结果，将结果写入数据库
    :param data:
    :param logger:
    :param query_id:
    :param start_time:
    :return:
    '''
    # 1. 计算目标cluster的时间和摄像头
    if data['camera_ids'] != 'all':
        sql = "select `timestamp`, `camera_id` from `t_cluster` where `cluster_id` = %s and `timestamp` between %s and %s and `camera_id` in {}".format(str(tuple(data['camera_ids'])))
    else:
        sql = "select `timestamp`, `camera_id` from `t_cluster` where `cluster_id` = %s and `timestamp` between %s and %s "
    select_result = db.select(sql, (data['cluster_id'], data['start'], data['end']))
    if select_result is None or len(select_result) == 0:
        logger.info('select from t_cluster error or result is null')
        return
    else:
        logger.info('select from t_cluster success')
        timestamps = list(map(lambda x:x[0], select_result))
        camera_ids = list(map(lambda x:x[1], select_result))
        # todo 同行人算法


@peer.route('/', methods=['POST'])
def peer():
    '''
    查询同行人
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    necessary_params = {'cluster_id','start', 'end','gap','min_times','threshold', 'start_pos', 'limit'}
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
        p = Process(target=compute, args=(data, logger, query_id, query_id))
        p.daemon = True
        p.start()
        proc_pool[query_id] = p
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['rtn'] = 0
        ret['query_id'] = query_id
        logger.info('启动peer compute 进程, process_key: ', query_id)
    else:
        # 2. 第二次查询，直接查表
        if data['query_id'] not in proc_pool:
            logger.info('query task %s 不存在' % data['query_id'])
            ret['rtn'] = -1
            ret['message'] = PEER_ERR['query_not_exist']
        elif proc_pool[data['query_id']].is_alive():
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
                  "on a.cluster_id = b.cluster_id and a.timestamp = b.anchor_time) c where c.cluster_id = x.cluster_id"
            select_result = db.select(sql, (data['query_id'], data['start_pos'], data['limit']))
            if select_result is None or len(select_result) ==0:
                logger.info('select from t_peer error or result is null')
                ret['rtn'] = -1
                ret['query_id'] = data['query_id']
                ret['message'] = PEER_ERR['fail']
            else:
                logger.info('select from t_peer success')
                ret['rtn'] = 0
                ret['query_id'] = data['query_id']
                ret['message'] = PEER_ERR['success']
                ret['status'] = PEER_ERR['done']
                cluster_ids = []
                imgs = []
                timess = []
                start_times = []
                end_times = []
                probs = []
                details = []

                for item in select_result:
                    if item[0] not in cluster_ids:
                        cluster_ids.append(item[0])
                        imgs.append(item[1])
                        timess.append(item[2])
                        start_times.append(item[3])
                        end_times.append(item[4])
                        probs.append(item[5])
                        detail = {'src_img': item[6], 'peer_img': item[7], 'src_time': item[8], 'peer_time': item[9], 'camera_id': item[10]}
                        details.append(detail)
                    else:
                        detail = {'src_img': item[6], 'peer_img': item[7], 'src_time': item[8], 'peer_time': item[9], 'camera_id': item[10]}
                        details.append(detail)
                ret['total'] = len(cluster_ids)
                ret['results'] = {'img': imgs, 'times': timess, 'start_time': start_times, 'end_time': end_times, 'prob': probs,'detail': details}
                ret['time_used'] = round((time.time() - start) * 1000)
    logger.info('peer api return: ', ret)
    return json.dumps(ret)