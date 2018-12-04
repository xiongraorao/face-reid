from flask import Blueprint, request
import json,time
from util.mysql import Mysql
from util.logger import Log
from rest.error import *
import configparser

search = Blueprint('search',__name__,)
logger = Log(__name__, is_save=False)
config = configparser.ConfigParser()
config.read('../app.config')
db = Mysql(host=config.get('db','host'),
                     port=config.getint('db','port'),
                     user=config.get('db', 'user'),
                     password=config.get('db','password'),
                     db=config.get('db','db'),
                     charset=config.get('db','charset'))
db.set_logger(logger)
default_param = {
    'topk': 100,
}
need_param = {'image_base64','start_pos','limit'}
all_param = need_param.copy()
all_param.update({'query_id','camera_ids','topk'})

def is_param_leagle(params):
    if len(need_param.difference(params)) == 0 and len(set(params).difference(all_param)) == 0:
        return True
    return False

def updata_param(default, input):
    ret = default.copy()
    ret.update(input)
    return ret

@search.route('/search', )
def search():
    '''
    人脸搜索，动态库检索
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    ret = {'time_used':0, 'rtn': -1}
    try:
        data = json.loads(data)
    except json.JSONDecodeError:
        logger.warning(GLOBAL_ERR['json_syntax_err'])
        ret['message'] = GLOBAL_ERR['json_syntax_err']
        return json.dumps(ret)
    if not is_param_leagle(data):
        logger.warning(GLOBAL_ERR['param_err'])
        ret['message'] = GLOBAL_ERR['param_err']
        return json.dumps(ret)
    # update parameters
    params = updata_param(default_param, data)

    # todo do search job
