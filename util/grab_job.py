import threading
import time


class GrabJob(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(GrabJob, self).__init__(*args, **kwargs)
        self.__flag = threading.Event()  # 用于暂停线程的标识
        self.__flag.set()  # 设置为True
        self.__running = threading.Event()  # 用于停止线程的标识
        self.__running.set()  # 设置为True
        self.grab = kwargs['grab']  # grab Object
        self.queue = kwargs['queue']  # output queue

    def run(self):
        try:
            while self.__running.isSet():
                self.__flag.wait()  # 为True时返回，为False阻塞
                # print('this is run')
                # time.sleep(1)
                img = self.grab.grab_image()
                if img is not None:
                    self.queue.put(img)
        except Exception as e:
            print(e)
            self.grab.close()
        finally:
            self.grab.close()

    def pause(self):
        self.__flag.clear()

    def resume(self):
        self.__flag.set()

    def stop(self):
        self.__flag.set()
        self.__running.clear()


if __name__ == '__main__':
    job = GrabJob()
    print('线程启动')
    job.start()
    time.sleep(10)
    print('线程暂停5s')
    job.pause()
    time.sleep(5)
    print('线程恢复')
    job.resume()
    time.sleep(10)
    print('线程终止')
    job.stop()
