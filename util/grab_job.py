import os
import queue
import sys
import threading
import time

# get current file dir
sup = os.path.dirname(os.path.realpath(__file__))
sup = os.path.dirname(sup)
if sup not in sys.path:
    sys.path.append(sup)

from util import Grab
from .mysql import Mysql
from .error import *


class GrabJob(threading.Thread):
    def __init__(self, img_queue, camera_id, url, rate, logger, config, max_retry=5):
        '''
        initialize ffmepg image grab Job
        :param img_queue:
        :param url:
        :param rate:
        :param logger:
        :param max_retry: grab失败后的最大尝试次数
        '''
        super(GrabJob, self).__init__()
        self.__flag = threading.Event()  # 用于暂停线程的标识
        self.__flag.set()  # 设置为True
        self.__running = threading.Event()  # 用于停止线程的标识
        self.__running.set()  # 设置为True
        self.queue = img_queue
        self.camera_id = camera_id
        self.url = url
        self.rate = rate
        self.logger = logger
        self.max_retry = max_retry
        self.db = Mysql(host=config.get('db', 'host'),
                        port=config.getint('db', 'port'),
                        user=config.get('db', 'user'),
                        password=config.get('db', 'password'),
                        db=config.get('db', 'db'),
                        charset=config.get('db', 'charset'))
        self.db.set_logger(logger)

    def __create(self):
        '''
        创建grab
        :return:
        '''
        g = Grab(self.url, self.rate, logger=self.logger)
        if g.initErr != 0:
            # 写入状态
            sql = 'update `t_camera` set state = %s where id = %s '
            ret = self.db.update(sql, (g.initErr, self.camera_id))
            if ret:
                self.logger.info([self.camera_id], '更新摄像头state成功')
            else:
                self.logger.info([self.camera_id], '更新摄像头state失败')
            self.logger.info([self.camera_id], '摄像头视频流初始化失败, %s ' % CAM_INIT_ERR[g.initErr])
            g.close()  # 关闭抓图进程
            return None
        else:
            self.logger.info([self.camera_id], '摄像头视频流初始化正常')
        return g

    def run(self):
        count = 0
        retried = 0
        grabber = self.__create()
        while self.__running.isSet():
            self.__flag.wait()  # 为True时返回，为False阻塞
            if grabber is not None:
                img = grabber.grab_image()
                if img is not None:
                    self.queue.put(img)
                    count = 0
                    retried = 0
                else:
                    count += 1
                    if count > 50:  # 连续50帧抓不到图，则释放资源
                        self.logger.warning([self.camera_id], '连续50帧抓图异常，退出抓图进程!')
                        grabber.close()
                        retried += 1
                        self.logger.warning([self.camera_id], 'grab thread retry... count = %d' % retried)
                        if retried > self.max_retry:
                            self.logger.error([self.camera_id], 'grab thread has retried %d times, exit' % retried)
                        else:
                            self.logger.warning([self.camera_id], 'restart grab thread...(%d)' % retried)
                            grabber.close()
                            grabber = self.__create()
                    self.logger.info([self.camera_id], 'grab image is null, count = %d' % count)
            else:
                self.logger.info([self.camera_id], 'grabber is None, recreate grabber ... (%d)' % retried)
                retried += 1
                if retried > self.max_retry:
                    self.logger.info([self.camera_id],
                                     'grabber is None, recreating grabber has retried %d times, exit' % retried)
                    break
        self.logger.info([self.camera_id], 'grab thread is over')

    def pause(self):
        self.__flag.clear()

    def resume(self):
        self.__flag.set()

    def stop(self):
        self.__flag.set()
        self.__running.clear()


if __name__ == '__main__':
    g = Grab('rtsp://admin:iec123456@192.168.1.71:554/unicast/c1/s0/live', 10)
    q = queue.Queue()
    job = GrabJob(grab=g, queue=q)
    print('线程启动')
    job.start()
    time.sleep(1)
    print('线程暂停5s')
    job.pause()
    time.sleep(10)  # 当抓取线程停顿时间较长，会报出data null的错误，ffmpeg本身没有buff，抓图不能太慢了
    print('线程恢复')
    job.resume()
    time.sleep(10)
    print('线程终止')
    job.stop()
