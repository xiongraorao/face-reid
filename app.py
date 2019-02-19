import configparser
import json
import threading
import time
import schedule

import pymysql
import requests
from flask import Flask

from rest import bp_camera, bp_search, bp_peer, bp_freq, bp_repo, bp_trace, watch_dog
from util import Mysql

app = Flask(__name__)
app.register_blueprint(bp_camera, url_prefix='/camera')
app.register_blueprint(bp_search, url_prefix='/search')
app.register_blueprint(bp_peer)
app.register_blueprint(bp_trace)
app.register_blueprint(bp_freq)
app.register_blueprint(bp_repo, url_prefix='/repository')

from util import Log

logger = Log('app', 'logs/')
config = configparser.ConfigParser()
config.read('./app.config')

# 设置数据库mode
conn = pymysql.connect(
    host=config.get('db', 'host'),
    port=config.getint('db', 'port'),
    user=config.get('db', 'user'),
    password=config.get('db', 'password'),
    connect_timeout=60
)
cur = conn.cursor()
cur.execute("alter database {} character set utf8;".format(config.get('db', 'db')))
cur.execute(
    "SET GLOBAL sql_mode = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION';")
cur.close()
conn.commit()
conn.close()

db = Mysql(host=config.get('db', 'host'),
           port=config.getint('db', 'port'),
           user=config.get('db', 'user'),
           password=config.get('db', 'password'),
           db=config.get('db', 'db'),
           charset=config.get('db', 'charset'))
db.set_logger(logger)

tables = [
    """
    CREATE TABLE IF NOT EXISTS `t_camera`(
  `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '摄像头ID',
  `name` VARCHAR(100) DEFAULT 'Default Camera' COMMENT '摄像头名称',
  `url` VARCHAR(100) NOT NULL COMMENT '摄像头RTSP地址',
  `rate` INT DEFAULT 1 COMMENT '抓帧频率',
  `grab` INT DEFAULT 1 COMMENT '0表示不开启抓图，1表示开启抓图',
  `state` INT DEFAULT 1 COMMENT '摄像头状态',
  `create_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
)default charset = utf8;
    """,
    """
    CREATE TABLE IF NOT EXISTS `t_cluster`(
  `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '人脸特征的索引ID, 样本ID',
  `cluster_id` VARCHAR(100) NOT NULL COMMENT '动态库聚类的ID',
  `uri` VARCHAR(100) NOT NULL COMMENT '抓拍人员的URI',
  `timestamp` TIMESTAMP NULL COMMENT '抓拍时间',
  `camera_id` INT NOT NULL COMMENT '抓拍摄像头的ID',
  `update_time` TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '重聚类的修改时间'
)default charset = utf8;
    """,
    """
    CREATE INDEX cluster ON `t_cluster`(cluster_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS `t_lib`(
  `repository_id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '人像库ID',
  `name` VARCHAR(100) NOT NULL COMMENT '人像库名称'
)default charset = utf8;
    """,
    """
    CREATE TABLE IF NOT EXISTS `t_person`(
  `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT 'person_id',
  `name` VARCHAR(100) NOT NULL COMMENT '人员名字，传入数据的person_id',
  `uri` VARCHAR(100) NOT NULL COMMENT '人员图片路径',
  `repository_id` INT NOT NULL COMMENT '人像库ID',
  FOREIGN KEY (`repository_id`) REFERENCES `t_lib`(`repository_id`)
    ON UPDATE CASCADE ON DELETE CASCADE
)default charset = utf8;
    """,
    """
    CREATE TABLE IF NOT EXISTS `t_contact`(
  `id` INT PRIMARY KEY COMMENT 'person_id，用于和动态库关联',
  `cluster_id` VARCHAR(100) NOT NULL COMMENT '动态库的类ID',
  `similarity` FLOAT COMMENT '该person和cluster_id的相似度',
  FOREIGN KEY (id) REFERENCES `t_person`(`id`) ON UPDATE CASCADE ON DELETE CASCADE
)default charset = utf8;
    """,
    """
    CREATE TABLE IF NOT EXISTS `t_search`(
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `cluster_id` VARCHAR(100) COMMENT '待查对象所属的类ID',
  `similarity` FLOAT COMMENT '相似度',
  `query_id` INT COMMENT 'query_id, 用于找到结果'
)default charset = utf8;
    """,
    """
    CREATE TABLE IF NOT EXISTS `t_peer`(
  `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '标识查询结果',
  `query_id` INT COMMENT 'query_id, 用于查找结果',
  `total` INT DEFAULT 0 COMMENT 'total result count',
  `cluster_id` VARCHAR(100) COMMENT '和目标同行的cluster_id',
  `times` INT COMMENT '目标人员和该cluster人员的同行次数',
  `start_time` TIMESTAMP COMMENT '开始同行时间',
  `end_time` TIMESTAMP COMMENT '结束同行时间',
  `prob` VARCHAR(10) COMMENT '两个人同行的概率'
)default charset = utf8;
    """,
    """
    CREATE TABLE IF NOT EXISTS `t_peer_detail`(
  `id` INT COMMENT '对应t_peer 表的id，用于存储具体的detail信息',
  `src_img` varchar(100) COMMENT '同行的某时刻的目标抓拍照',
  `peer_img` varchar(100) COMMENT '同行的某时刻的同行人抓拍照',
  `src_time` TIMESTAMP COMMENT '同行的某时刻的目标抓拍时间',
  `peer_time` TIMESTAMP COMMENT '同行的某时刻的同行人抓拍时间',
  `camera_id` INT COMMENT '在具体的哪一个摄像机下同行'
)default charset = utf8;
    """
]


def init():
    '''
    读取数据库中camera的状态，自动启动抓图进程
    :return:
    '''
    # 创建表
    for table in tables:
        db.update(table)
        db.commit()
    time.sleep(5)
    sql = "select id, rate, grab, name, url from `t_camera` where grab = %s"
    ret = db.select(sql, 1)
    for item in ret:
        logger.info('initialize ', item, 'camera, auto start grabbing')
        # 发送update请求，自动开启抓图
        headers = {'content-type': "application/json"}
        url = 'http://localhost:5000/camera/update'
        data_request = {'id': item[0], 'rate': item[1], 'grab': item[2], 'name': item[3], 'url': item[4]}
        print('request parmas: ', json.dumps(data_request, ensure_ascii=False))
        response = requests.post(url, data=json.dumps(data_request), headers=headers)
        logger.info('camera id =', id, ', response: ', response.json())
        time.sleep(5) # 延迟启动抓图进程，否则起不来
    logger.info('camera task initialize complete')

def check_grab():
    logger.info('====start process_pool watch dog====')
    schedule.every(5).minutes.do(watch_dog, logger) # 每间隔5分钟检查一次抓图进程
    while True:
        schedule.run_pending()

if __name__ == '__main__':
    t = threading.Thread(target=init)
    t.start()
    t2 = threading.Thread(target=check_grab)
    t2.start()
    app.run('0.0.0.0')
