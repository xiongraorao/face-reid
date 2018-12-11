import configparser
import json
import asyncio
import requests
import time
import threading
from flask import Flask

from rest import camera
from util.logger import Log
from util.mysql import Mysql

app = Flask(__name__)
app.register_blueprint(camera, url_prefix='/camera')

# todo 初始化的时候，读取数据库中camera的状态，自动启动抓图进程

logger = Log('app', 'logs/')
config = configparser.ConfigParser()
config.read('./app.config')

db = Mysql(host=config.get('db', 'host'),
           port=config.getint('db', 'port'),
           user=config.get('db', 'user'),
           password=config.get('db', 'password'),
           db=config.get('db', 'db'),
           charset=config.get('db', 'charset'))
db.set_logger(logger)

def init():
    '''
    读取数据库中camera的状态，自动启动抓图进程
    :return:
    '''
    time.sleep(5)
    sql = "select id, rate, grab, name, url from `t_camera` where grab = %s"
    ret = db.select(sql, 1)
    for item in ret:
        logger.info('initialize ', item, 'camera, auto start grabbing')
        # 发送update请求，自动开启抓图
        headers = {'content-type': "application/json"}
        url = 'http://localhost:5000/camera/update'
        data_request = {'id': item[0], 'rate': item[1],'grab': item[2], 'name': item[3], 'url': item[4]}
        print('request parmas: ', json.dumps(data_request,ensure_ascii=False))
        response = requests.post(url,data=json.dumps(data_request), headers=headers)
        logger.info('camera id =', id, ', response: ', response.json())
    logger.info('camera task initialize complete')

if __name__ == '__main__':
    t = threading.Thread(target=init)
    t.start()
    app.run('0.0.0.0')