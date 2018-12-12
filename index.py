'''
程序入口
'''
import base64
import configparser
import json
import uuid

import cv2
import numpy as np
import requests
import time

from util.date import time_to_date
from util.face import mat_to_base64, Face
from util.logger import Log
from util.mykafka import Kafka
from util.mysql import Mysql
from util.search import Search
from util.face import bytes_to_base64

logger = Log('index', 'logs/')
config = configparser.ConfigParser()
config.read('./app.config')


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
    for msg in consumer:
        logger.info('get msg: ', msg)
        msg = msg.value
        start = round(time.time())
        msg = json.loads(msg)
        b64 = download(msg['url'])
        landmark = msg['landmark']
        feature = face_tool.extract([b64], [landmark])
        print(feature)
        feature = feature['feature'][0]

        # 1. 添加数据库，获取sample_id
        cluster_id = hash(uuid.uuid4())
        sql = "insert into `t_cluster` (`cluster_id`, `uri`, `timestamp`, `camera_id`) values (%s, %s, %s, %s)"
        sample_id = db.insert(sql, (cluster_id, msg['url'], time_to_date(int(msg['time'])), msg['camera_id']))
        if sample_id == -1:
            logger.info('sample insert failed, mysql maybe not available')
            continue
        db.commit()

        # 2. 添加特征到索引中
        searcher = Search(config.get('api', 'search_host'), config.getint('api', 'search_port'))
        print('dim: ', len(feature))
        ret = searcher.add([sample_id], [feature])
        logger.info('index add:', ret)

        # 3. 进行预分类
        s_res = searcher.search(1, [feature])
        print('search result', s_res)
        sim = s_res['result']['0']['distance'][0]
        label = s_res['result']['0']['labels'][0]
        if sim > 0.75:
            # 合并成一个类
            sql = "update `t_cluster` as a inner join `t_cluster` as b on a.id = %s and b.id = %s set b.cluster_id = a.cluster_id"
            ret = db.update(sql, (label, sample_id))
            if ret:
                db.commit()
                logger.info('merge into the same cluster, %s -> %s' % (sample_id, label))
            else:
                logger.info('sample update failed, mysql maybe not available')
        else:
            # 新建一个类
            pass

        lantency = round(time.time()) - start
        logger.info('process lantency:', lantency)

if __name__ == '__main__':
    process()
