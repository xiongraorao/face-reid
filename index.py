'''
程序入口
'''
import configparser
import json

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

logger = Log('index', 'logs/')
config = configparser.ConfigParser()
config.read('./app.config')


def download(url):
    content = requests.get(url).content
    ret = cv2.imdecode(np.fromstring(content, np.uint8), cv2.IMREAD_COLOR)
    return ret


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
    face = Face(config.get('api', 'face_server'))
    cluster_id = 0
    for msg in consumer:
        logger.info('get msg: ', msg)
        msg = json.loads(msg.value.decode('utf-8'))
        start = round(time.time())
        msg = json.loads(msg)
        img = download(msg['url'])
        b64 = mat_to_base64(img)
        landmark = msg['landmark']
        feature = face.extract(b64, landmark)

        # 1. 添加数据库，获取sample_id

        sql = "insert into `t_cluster` (`cluster_id`, `uri`, `timestamp`, `camera_id`) values (%s, %s, %s, %s)"
        sample_id = db.insert(sql, (cluster_id, msg['url'], time_to_date(msg['time']), msg['camera_id']))
        if sample_id == -1:
            logger.info('sample insert failed, mysql maybe not available')
            continue
        db.commit()

        # 2. 添加特征到索引中
        searcher = Search(config.get('api', 'search_host'), config.getint('api', 'search_port'))
        ret = searcher.add([sample_id], [feature])
        logger.info('index add:', ret)

        # 3. 进行预分类
        s_res = searcher.search(1, [feature])
        sim = s_res['result'][0]['distance'][0]
        label = s_res['result'][0]['label'][0]
        if sim > 0.75:
            # 合并成一个类
            sql = "update `t_cluster` set `cluster_id` = (select cluster_id from `t_cluster` where id = %s) where id = %s"
            ret = db.update(sql, (label, sample_id))
            if ret:
                db.commit()
                logger.info('merge into the same cluster, %s -> %s' % (sample_id, label))
            else:
                logger.info('sample update failed, mysql maybe not available')
        else:
            # 新建一个类
            cluster_id += 1  # 更新cluster_id 下次使用
        lantency = round(time.time()) - start
        logger.info('process lantency:', lantency)

if __name__ == '__main__':
    process()
