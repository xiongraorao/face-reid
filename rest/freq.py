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
from .param_tool import check_param, update_param, check_date
from util import time_to_date
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

freq = Blueprint('freq', __name__)


@freq.route('/', methods=['POST'])
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

    legal = check_param(set(data), necessary_params, set(default_params))
    if not legal:
        logger.warning(GLOBAL_ERR['param_err'])
        ret['message'] = GLOBAL_ERR['param_err']
        return json.dumps(ret)
    # check start end 格式问题
    b_date = check_date(data['start'], data['end'])
    if not b_date:
        logger.warning(FREQ_ERR['time_format_err'])
        ret['message'] = FREQ_ERR['time_format_err']
        return json.dumps(ret)
    data = update_param(default_params, data)
    logger.info('parameters:', data)

    if data['camera_ids'] == 'all':
        sql = "select timestamp from `t_cluster` where timestamp between %s and %s " \
              "where cluster_id = %s order by timestamp desc limit %s, %s"
        select_result = db.select(sql,
                                  (data['start'], data['end'], data['cluster_id'], data['start_pos'], data['limit']))
        if select_result is None or len(select_result) == 0:
            logger.info('select failed or result is null')
        else:
            logger.info('select success')

            raw_result = {}
            result = []
            for item in select_result:
                t = time_to_date(item[0])
                key = t[:10]  # 2018-12-14
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
