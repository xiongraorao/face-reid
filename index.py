'''
程序入口
'''
import configparser
import json
import time
import uuid

import requests

from util import Face
from util import Faiss
from util import Kafka
from util import Log
from util import Mysql
from util import bytes_to_base64
from util import time_to_date
from util import trans_sqlin

logger = Log('index', 'logs/')
config = configparser.ConfigParser()
config.read('./app.config')
threshold = 0.75  # 判断人脸特征的阈值
topk = 5

def download(url):
    '''
    download image as base64
    :param url:
    :return:
    '''
    content = requests.get(url).content
    b64 = bytes_to_base64(content)
    return b64

def process():
    # 1.从kafka消费消息
    kafka = Kafka(bootstrap_servers=config.get('kafka', 'boot_servers'))
    db = Mysql(host=config.get('db', 'host'),
               port=config.getint('db', 'port'),
               user=config.get('db', 'user'),
               password=config.get('db', 'password'),
               db=config.get('db', 'db'),
               charset=config.get('db', 'charset'))
    db.set_logger(logger)
    topics = config.get('camera', 'topic')
    consumer = kafka.get_consumer(topics, 'default')
    face_tool = Face(config.get('api', 'face_server'))
    searcher = Faiss(config.get('api', 'faiss_host'), config.getint('api', 'faiss_port'))
    count = 0
    for msg in consumer:
        logger.info('get msg: ', msg)
        msg = msg.value
        start = round(time.time())
        msg = json.loads(msg)
        b64 = download(msg['url'])
        landmark = msg['landmark']
        feature = face_tool.extract([b64], [landmark])
        feature = feature['feature'][0]

        # get one unique cluster_id
        cluster_id = str(hash(uuid.uuid4()))

        # 1. 进行预分类
        search_result = searcher.search(1, topk, [feature])
        if search_result['rtn'] == 0:
            logger.info('index search successfully, return result: ', search_result)
        else:
            logger.info('index search failed, return result: ', search_result)

        # 4. 计算cluster的平均相似度，然后合并
        dist_lable = list(map(lambda x, y: (x, y), search_result['results']['distances'][0],
                              search_result['results']['lables'][0]))
        # 过滤掉低于给定阈值相似度的向量
        dist_lable = list(filter(lambda x: x[0] > threshold, dist_lable))
        distances = list(map(lambda x: x[0], dist_lable))
        lables = list(map(lambda x: x[1], dist_lable))
        logger.info('real topk is:', len(lables))

        if len(lables) == 0:
            # 新建一个类
            logger.info('new a cluster, cluster_id:', cluster_id)

            # 插入数据库和索引中
            sql = "insert into `t_cluster` (`cluster_id`, `uri`, `timestamp`, `camera_id`) values (%s, %s, %s, %s)"
            sample_id = db.insert(sql, (cluster_id, msg['url'], time_to_date(int(msg['time'])), msg['camera_id']))
            if sample_id == -1:
                logger.info('sample insert failed, mysql maybe not available')
                continue
            db.commit()
        else:
            logger.info('start merge into another cluster')
            # 统计属于哪个cluster
            sql = "select `cluster_id` from t_cluster where id in {} order by field (id, {}) " \
                .format(trans_sqlin(lables), trans_sqlin(lables)[1:-1])
            select_result = db.select(sql)
            if select_result is not None and len(select_result) > 0:
                logger.info('select from t_cluster successfully, size: ', len(select_result))
                clusters = list(map(lambda x: x[0], select_result))
                assert len(clusters) == len(distances), 'cluster select error'

                cluster_dic = {}  # cluster-> [distance1, distance2...]
                for j in range(len(clusters)):
                    if clusters[j] not in cluster_dic:
                        cluster_dic[clusters[j]] = [distances[j]]
                    else:
                        cluster_dic[clusters[j]].append(distances[j])
                for k, v in cluster_dic.items():
                    cluster_dic[k] = sum(v) / len(v)  # 每个cluster和目标对应的平均相似度
                # 按照value的值从大到小排序, 取最大的cluster的相似度
                cluster_sim = sorted(list(cluster_dic.items()), key=lambda x: x[1], reverse=True)[0]

                # 合并成一个类
                # 插入数据库和索引中
                sql = "insert into `t_cluster` (`cluster_id`, `uri`, `timestamp`, `camera_id`) values (%s, %s, %s, %s)"
                sample_id = db.insert(sql, (cluster_sim[0], msg['url'], time_to_date(int(msg['time'])), msg['camera_id']))
                if sample_id == -1:
                    logger.info('sample insert failed, mysql maybe not available')
                else:
                    logger.info('merge into the same cluster, %s -> %s' % (sample_id, cluster_sim[0]))
                    db.commit()
            else:
                logger.info('select from t_cluster failed, mysql maybe not available')
                logger.info('discard this image')
                continue

        # 添加特征到索引中
        logger.info('add feature to index server')
        add_result = searcher.add(1, [sample_id], [feature])
        if add_result['rtn'] == 0:
            logger.info('index add successfully, return result:', add_result)
        else:
            logger.info('index add failed, return result:', add_result)

        lantency = round(time.time()) - start
        count += 1
        logger.info('process lantency: %d, count = %d' % (lantency,count))

if __name__ == '__main__':
    process()
