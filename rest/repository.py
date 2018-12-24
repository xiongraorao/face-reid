import configparser
import json
import os
import sys
import threading
import time

from flask import Blueprint, request

# get current file dir
sup = os.path.dirname(os.path.realpath(__file__))
sup = os.path.dirname(sup)
if sup not in sys.path:
    sys.path.append(sup)

from .error import *
from .param_tool import check_param, update_param
from util import Face, WeedClient, base64_to_bytes, trans_sqlin, trans_sqlinsert
from util import Log
from util import Mysql
from util import Faiss
from util import get_as_base64

logger = Log('repository', 'logs/')
config = configparser.ConfigParser()
config.read('./app.config')

db = Mysql(host=config.get('db', 'host'),
           port=config.getint('db', 'port'),
           user=config.get('db', 'user'),
           password=config.get('db', 'password'),
           db=config.get('db', 'db'),
           charset=config.get('db', 'charset'))
db.set_logger(logger)
bp_repo = Blueprint('repository', __name__)

face_tool = Face(config.get('api', 'face_server'))
searcher = Faiss(config.get('api', 'faiss_host'), config.getint('api', 'faiss_port'))
weed_client = WeedClient(config.get('weed', 'host'), config.getint('weed', 'port'))
threshold = 0.75  # 用于过滤找到的topk人脸
topk = 100


@bp_repo.route('/test', methods=['GET'])
def test():
    contact(5)
    return 'ssss'

def contact(repository_id):
    '''
    静态库和动态库的关联过程
    :param repository_id:
    :return:
    '''
    # 1. 查询数据库
    sql = "select `id`, `uri` from `t_person` where `repository_id` = %s "
    select_result = db.select(sql, repository_id)
    ids = []
    img_base64 = []
    landmarks = []
    if len(select_result) == 0 or select_result is None:
        logger.info('select from t_person error')
    else:
        size = len(select_result)
        logger.info('selected %d items from t_person' % size)
        for item in select_result:
            b64 = get_as_base64(item[1])
            if b64 is None:
                logger.info('url is invalid or image server has down, please check seaweedfs')
                continue
            else:
                detect_result = face_tool.detect(b64, 'portrait')
                if detect_result['error_message'] != '601' or detect_result['detect_nums'] == 0:
                    logger.info('detect 0 face or detect error, error_code:', detect_result['error_message'])
                else:
                    logger.info('detect %d face successfully' % detect_result['detect_nums'])
                    left = detect_result['detect'][0]['left']
                    top = detect_result['detect'][0]['top']
                    width = detect_result['detect'][0]['width']
                    height = detect_result['detect'][0]['height']
                    cropped_img = face_tool.crop(left, top, width, height, b64, True)
                    landmark = detect_result['detect'][0]['landmark']
                    img_base64.append(cropped_img)
                    landmarks.append(landmark)
                    ids.append(item[0])
    # 2. 特征比对
    logger.info('start extract features in batch')
    extract_result = face_tool.extract(img_base64, landmarks)
    if extract_result['error_message'] != '701':
        logger.info('extract features error, error code: ', extract_result['error_message'])
    else:
        features = extract_result['feature']
        assert len(features) == len(ids), 'extract feature error, not exactly'
        logger.info('extract features successfully, count = %d' % len(features))

        # 3. 向动态库检索
        logger.info('start search in index server, topk = %d' % topk)
        search_result = searcher.search(len(features), topk, features)
        if search_result['rtn'] != 0:
            logger.info('search error, seacher service may be down')
        else:
            logger.info('search successfully, used_time = %d ms' % search_result['time_used'])
            cluster_ids = []
            sims = []
            for i in range(len(features)):
                dist_lable = list(map(lambda x, y: (x, y), search_result['results']['distances'][i],
                                      search_result['results']['lables'][i]))
                dist_lable = list(filter(lambda x: x[0] > threshold, dist_lable))  # 过滤掉阈值小于threshold 的dist_lable 对
                distances = list(map(lambda x: x[0], dist_lable))
                lables = list(map(lambda x: x[1], dist_lable))
                # select cluster
                t_sql = "select `cluster_id` from `t_cluster` where id in {} order by field (id, {})" \
                    .format(trans_sqlin(lables), trans_sqlin(lables)[1:-1])
                t_result = db.select(t_sql)
                if t_result is None or len(t_result) == 0:
                    logger.info('select t_cluster error or t_cluster is null or person not match to t_cluster')
                else:
                    logger.info('select t_cluster successfully')
                    clusters = list(map(lambda x: x[0], t_result))
                    assert len(clusters) == len(distances), 'cluster select error'
                    # 统计属于哪个cluster
                    cluster_dic = {}  # {'cluster': [d1， d2] }
                    for j in range(len(clusters)):
                        if clusters[j] not in cluster_dic:
                            cluster_dic[clusters[j]] = [distances[j]]
                        else:
                            cluster_dic[clusters[j]].append(distances[j])
                    for k, v in cluster_dic.items():
                        cluster_dic[k] = sum(v) / len(v)  # 每个cluster和目标对应的平均相似度
                    cluster_id, sim = sorted(list(cluster_dic.items()), key=lambda x: x[1], reverse=True)[
                        0]  # 按照value的值从大到小排序，取最大值
                    cluster_ids.append(cluster_id)
                    sims.append(sim)

            # 4. 找到关系之后，插入contact表
            values = tuple(map(lambda x, y, z: (x, y, z), ids, cluster_ids, sims))
            t_sql = "insert into `t_contact`(`id`, `cluster_id`, `similarity`) values {}".format(
                trans_sqlinsert(values))
            insert_result = db.insert(t_sql)
            if insert_result == -1:
                logger.info('insert data into t_contact error, or insert values is null')
            else:
                logger.info('insert data into t_contact successfully')
                db.commit()


@bp_repo.route('/add', methods=['POST'])
def repo_add():
    '''
    新建人像库
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    necessary_params = {'name'}
    default_params = {}
    ret = {'time_used': 0, 'rtn': -1, 'id': -1}
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

    sql = "insert into `t_lib` (`name`) values (%s)"
    repo_id = db.insert(sql, (data['name']))
    ret['id'] = repo_id
    if repo_id == -1:
        logger.info('添加人像库失败')
        ret['rtn'] = -2
        ret['message'] = REPO_ERR['fail']
    else:
        logger.info('添加人像库成功')
        ret['rtn'] = 0
        ret['message'] = REPO_ERR['success']
        ret['time_used'] = round((time.time() - start) * 1000)
        db.commit()

    logger.info('repository add api return: ', ret)
    return json.dumps(ret)


@bp_repo.route('/del', methods=['POST'])
def repo_del():
    '''
    删除人像库
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    necessary_params = {'id'}
    default_params = {}
    ret = {'time_used': 0, 'rtn': -1}
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

    sql = "delete from `t_lib` where `repository_id` = %s"
    result = db.delete(sql, (data['id']))
    if result:
        logger.info('人像库删除成功')
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['rtn'] = 0
        ret['message'] = REPO_ERR['success']
        db.commit()
    else:
        logger.info('人像库删除失败')
        ret['message'] = REPO_ERR['fail']

    logger.info('repository delete api return: ', ret)
    return json.dumps(ret)


@bp_repo.route('/update', methods=['POST'])
def repo_update():
    '''
    更新人像库
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    necessary_params = {'id', 'name'}
    default_params = {}
    ret = {'time_used': 0, 'rtn': -1}
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

    sql = "update `t_lib` set `name` = %s where repository_id = %s"
    result = db.update(sql, (data['name'], data['id']))
    if result:
        logger.info('人像库更新成功')
        ret['time_used'] = round((time.time() - start) * 1000)
        ret['rtn'] = 0
        ret['message'] = REPO_ERR['success']
        db.commit()
    else:
        logger.info('人像库更新失败')
        ret['message'] = REPO_ERR['fail']

    logger.info('repository update api return: ', ret)
    return json.dumps(ret)


@bp_repo.route('/repos', methods=['GET'])
def repos():
    '''
    获取所有的id库，以及库对应的人
    :return:
    '''
    start = time.time()
    ret = {'time_used': 0, 'rtn': -1}
    sql = "select t_lib.repository_id, t_lib.name, count(*) from `t_lib` left join t_person p on p.repository_id = t_lib.repository_id group by t_lib.repository_id"
    result = db.select(sql)
    if len(result) == 0 or result is None:
        logger.info('查询人像库失败')
        ret['message'] = REPO_ERR['fail']
    else:
        logger.info('查询人像库成功')
        ret['rtn'] = 0
        ret['message'] = REPO_ERR['success']
        repositories = []
        for item in result:
            repo = {'id': item[0], 'name': item[1], 'total': item[2]}
            repositories.append(repo)
        ret['repositories'] = repositories
        ret['time_used'] = round((time.time() - start) * 1000)

    logger.info('repository get all api return: ', ret)
    return json.dumps(ret)


@bp_repo.route('/picture/batch_uri', methods=['POST'])
def picture_add():
    '''
    批量添加图片
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    necessary_params = {'repository_id', 'path'}
    default_params = {}
    ret = {'time_used': 0, 'rtn': -1, 'id': -1}
    # 检查json 格式
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
    logger.info('parameters: ', data)

    img_list = list(filter(lambda x: x.split('.')[-1] == 'jpg', os.listdir(data['path'])))
    img_list = list(map(lambda x: os.path.join(data['path'], x), img_list))
    urls = []  # uploaded file's url in seaweedFS
    person_ids = []  # person_id 人的名字
    for img in img_list:
        person_ids.append(os.path.split(img)[-1][:-4])
        with open(img, 'rb') as f:
            assign = weed_client.assign()
            upload_result = weed_client.upload(assign['url'], assign['fid'], f.read(), img)
            logger.info('upload result: ', upload_result)
            url = 'http://' + assign['url'] + '/' + assign['fid']
            urls.append(url)
            logger.info('upload %s to seaweedFS with url: %s' % (img, url))

    assert len(img_list) == len(urls) == len(person_ids), '上传图片错误'

    # 将静态库数据写入mysql中
    values = tuple(map(lambda x, y, z: (x, y, z), person_ids, urls, tuple([data['repository_id']] * len(img_list))))
    sql = "insert into `t_person`(`name`, `uri`, `repository_id`) values {}".format(trans_sqlinsert(values))
    insert_result = db.insert(sql)
    if insert_result == -1:
        logger.info('insert data into t_person error')
        ret['message'] = REPO_ERR['fail']
    else:
        logger.info('insert data into t_person successfully')
        ret['rtn'] = 0
        ret['message'] = REPO_ERR['success']
        ret['time_used'] = round((time.time() - start) * 1000)
        db.commit()
        # 启动一个线程完成静态库和动态库的关联过程
        t = threading.Thread(target=contact, args=(data['repository_id']))
        t.start()

    return json.dumps(ret)


@bp_repo.route('/picture/batch_image', methods=['POST'])
def picture_add2():
    '''
    通过base64编码批量导入
    :return:
    '''
    start = time.time()
    data = request.data.decode('utf-8')
    necessary_params = {'repository_id', 'images'}
    default_params = {}
    ret = {'time_used': 0, 'rtn': -1, 'id': -1}
    # 检查json 格式
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

    person_ids = list(map(lambda x: x['person_id'], data['images']))
    image_base64s = list(map(lambda x: x['image_base64'], data['images']))

    urls = []
    # upload to seaweed fs
    for b64 in image_base64s:
        assign = weed_client.assign()
        upload_result = weed_client.upload(assign['url'], assign['fid'], base64_to_bytes(b64))
        logger.info('upload result: ', upload_result)
        url = 'http://' + assign['url'] + '/' + assign['fid']
        urls.append(url)
        logger.info('upload to seaweedFS with url: %s' % url)
    assert len(image_base64s) == len(person_ids) == len(urls), '上传图片错误，或者参数长度不匹配'

    # 将静态库数据写入mysql中
    values = tuple(map(lambda x, y, z: (x, y, z), person_ids, urls, tuple(data['repository_id'] * len(image_base64s))))
    sql = "insert into `t_person`(`person_id`, `uri`, `repository_id`) values {}".format(trans_sqlinsert(values))
    insert_result = db.insert(sql)
    if insert_result == -1:
        logger.info('insert data into t_person error')
        ret['message'] = REPO_ERR['fail']
    else:
        logger.info('insert data into t_person successfully')
        ret['rtn'] = 0
        ret['message'] = REPO_ERR['success']
        ret['time_used'] = round((time.time() - start) * 1000)
        db.commit()

    # 启动一个线程完成静态库和动态库的关联过程
    t = threading.Thread(target=contact, args=(data['repository_id']))
    t.start()
    return json.dumps(ret)
