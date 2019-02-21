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
from util import Log, get_db_client, trans_sqlin

logger = Log('freq', 'logs/')
config = configparser.ConfigParser()
config.read('./app.config')
bp_freq = Blueprint('freq', __name__)


@bp_freq.route('/freq', methods=['POST'])
def freq():
    '''
    频次查询，查表
    :return:
    '''
    start = time.time()
    db = get_db_client(config, logger)
    data = request.data.decode('utf-8')
    necessary_params = {'freq', 'start', 'end', 'start_pos', 'limit'}
    default_params = {'camera_ids': 'all'}
    ret = {'time_used': 0, 'rtn': -1}
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
    v = [data['start'], data['end'], data['freq'], data['start_pos'], data['limit']]
    legal = check_param_value(p, v)
    if not legal:
        logger.warning(GLOBAL_ERR['value_err'])
        ret['message'] = GLOBAL_ERR['value_err']
        return json.dumps(ret)
    data = update_param(default_params, data)

    if data['camera_ids'] == 'all':
        sql = "select cluster_id, timestamp, uri, camera_id from `t_cluster` where timestamp between %s and %s order by timestamp desc"
    else:
        sql = "select cluster_id, timestamp, uri, camera_id from `t_cluster` where (timestamp between %s and %s) and camera_id in {}  order by timestamp desc".format(trans_sqlin(data['camera_ids']))
    select_result = db.select(sql, (data['start'], data['end']))
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
        cluster_ts = {}  # cluster_id times_stamp
        cluster_anchors = {}  # cluster_id anchor_img
        for item in select_result:
            if item[0] not in cluster_ts:
                cluster_ts[item[0]] = [item[1]]
            else:
                cluster_ts[item[0]].append(item[1])
            if item[0] not in cluster_anchors:
                cluster_anchors[item[0]] = [(item[2], item[3])]
            else:
                cluster_anchors[item[0]].append((item[2], item[3]))
        results = []
        for cluster_id in cluster_ts:
            raw_result = {}
            for ts in cluster_ts[cluster_id]:
                key = str(ts.date())  # 2018-12-14
                raw_result[key] = 1 if key not in raw_result else raw_result[key] + 1
            if len(raw_result) < data['freq']:
                continue
            else:
                person_info = {'cluster_id': cluster_id, 'anchor_img': cluster_anchors[cluster_id][0][0],
                               'last_camera': cluster_anchors[cluster_id][0][1]}
                person_freq = []
                for k, v in raw_result.items():
                    temp = {'date': k, 'times': v}
                    person_freq.append(temp)
                person_info['freq'] = person_freq
                dts = sorted(cluster_ts[cluster_id])
                person_info['start_time'] = dts[0].strftime('%Y-%m-%d %H:%M:%S')
                person_info['end_time'] = dts[-1].strftime('%Y-%m-%d %H:%M:%S')
            results.append(person_info)

        ret['total'] = len(results)
        if data['start_pos'] + data['limit'] < len(results):
            ret['results'] = results[data['start_pos']:(data['start_pos'] + data['limit'])]
        else:
            ret['results'] = results[data['start_pos']:]
        ret['rtn'] = 0
        ret['message'] = FREQ_ERR['success']
        ret['time_used'] = round((time.time() - start) * 1000)
    logger.info('frequency api return: ', ret)
    db.close()
    return json.dumps(ret)
