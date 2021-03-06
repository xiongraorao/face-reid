import configparser
import json
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
from .param_tool import check_param_key, update_param, G_RE, check_param_value
from util import Log, trans_sqlin
from util import Mysql

logger = Log('trace', 'logs/')
config = configparser.ConfigParser()
config.read('./app.config')

db = Mysql(host=config.get('db', 'host'),
           port=config.getint('db', 'port'),
           user=config.get('db', 'user'),
           password=config.get('db', 'password'),
           db=config.get('db', 'db'),
           charset=config.get('db', 'charset'))
db.set_logger(logger)

bp_trace = Blueprint('trace', __name__)

@bp_trace.route('/trace', methods=['POST'])
def trace():
    '''
    判断轨迹，查表
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    necessary_params = {'cluster_id','start', 'end', 'start_pos', 'limit'}
    default_params = {'query_id': -1, 'camera_ids': 'all', 'order': 1}
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
    # check start end 格式问题
    p = [G_RE['datetime'], G_RE['datetime'], G_RE['num'], G_RE['num'], G_RE['num']]
    v = [data['start'], data['end'], data['cluster_id'], data['start_pos'], data['limit']]
    legal = check_param_value(p, v)
    if not legal:
        logger.warning(GLOBAL_ERR['value_err'])
        ret['message'] = GLOBAL_ERR['value_err']
        return json.dumps(ret)
    data = update_param(default_params, data)

    if data['camera_ids'] == 'all':
        sql = "select c.timestamp, c.uri, c.camera_id from `t_cluster` as c where c.cluster_id = %s and  c.timestamp between %s and %s " \
              "order by c.timestamp desc  limit %s, %s"
    else:
        sql = "select c.timestamp, c.uri, c.camera_id from `t_cluster` as c where c.cluster_id = %s and  c.timestamp between %s and %s and c.camera_id in {} " \
              "order by c.timestamp desc limit %s, %s ".format(trans_sqlin(data['camera_ids']))
    select_result = db.select(sql, (data['cluster_id'], data['start'], data['end'], data['start_pos'], data['limit']))
    if select_result is None or len(select_result) == 0:
        logger.info('select failed or result is null')
    else:
        logger.info('select success')
        results = []
        for item in select_result:
            result = {'grab_time': item[0].strftime('%Y-%m-%d %H:%M:%S'), 'img': item[1], 'camera_id': item[2]}
            results.append(result)
        if data['order'] == 2:
            # 按照时间正序输出
            results = results[::-1]
        ret['results'] = results
        ret['query_id'] = -1
        ret['total'] = len(select_result)
        ret['rtn'] = 0
        ret['message'] = TRACE_ERR['success']
        ret['time_used'] = round((time.time() - start) * 1000)
    logger.info('trace api return: ', ret)
    return json.dumps(ret)
