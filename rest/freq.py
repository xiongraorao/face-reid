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
from .param_tool import check_param_key, update_param, check_param_value, G_RE
from util import Log
from util import Mysql

logger = Log('freq', 'logs/')
config = configparser.ConfigParser()
config.read('./app.config')

db = Mysql(host=config.get('db', 'host'),
           port=config.getint('db', 'port'),
           user=config.get('db', 'user'),
           password=config.get('db', 'password'),
           db=config.get('db', 'db'),
           charset=config.get('db', 'charset'))
db.set_logger(logger)

bp_freq = Blueprint('freq', __name__)


@bp_freq.route('/freq', methods=['POST'])
def freq():
    '''
    频次查询，查表
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    necessary_params = {'cluster_id', 'freq', 'start', 'end', 'start_pos', 'limit'}
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
    p = [G_RE['datetime'], G_RE['datetime'], G_RE['num'], G_RE['num'], G_RE['num'], G_RE['num']]
    v = [data['start'], data['end'], data['cluster_id'], data['freq'], data['start_pos'], data['limit']]
    legal = check_param_value(p, v)
    if not legal:
        logger.warning(GLOBAL_ERR['value_err'])
        ret['message'] = GLOBAL_ERR['value_err']
        return json.dumps(ret)
    data = update_param(default_params, data)

    if data['camera_ids'] == 'all':
        sql = "select timestamp from `t_cluster` where timestamp between %s and %s " \
              "and cluster_id = %s order by timestamp desc limit %s, %s"
        select_result = db.select(sql,
                                  (data['start'], data['end'], data['cluster_id'], data['start_pos'], data['limit']))
        if select_result is None:
            logger.warning('SQL select exception')
            ret['rtn'] = -2
            ret['message'] = FREQ_ERR['fail']
        elif len(select_result) == 0:
            logger.info('select result is null')
            ret['rtn'] = 0
            ret['message'] = GLOBAL_ERR['null']
        else:
            logger.info('select success')
            raw_result = {}
            result = []
            for item in select_result:
                # item 为datatime类型
                key = str(item[0].date())  # 2018-12-14
                raw_result[key] = 1 if key not in raw_result else raw_result[key] + 1
            for k, v in raw_result.items():
                if v < data['freq']:
                    del raw_result[k]
                else:
                    temp = {'data': k, 'times': v}
                    result.append(temp)
            ret['total'] = len(raw_result)
            ret['results'] = result
            ret['rtn'] = 0
            ret['message'] = FREQ_ERR['success']
            ret['time_used'] = round((time.time() - start) * 1000)
    logger.info('frequency api return: ', ret)
    return json.dumps(ret)