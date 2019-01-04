'''
测试docker多进程的问题
'''
import queue
import time
from multiprocessing import Process
from threading import Thread


def _main():
    while True:
        time.sleep(3)
        print('this is main function')


def proc():
    subt = Thread(target=tee)
    subt.start()
    while True:
        time.sleep(2)
        print('this is sub process')


def proc2():
    q = queue.Queue()
    t = T(q)
    # t = Thread(target=tee)
    t.start()
    while True:
        time.sleep(2)
        print('ok')
        print('this is sub process, get value from queue: ', q.get())


def tee():
    while True:
        time.sleep(2)
        print('this is thread in sub process')


class T(Thread):
    def __init__(self, q):
        super(T, self).__init__()
        self.q = q

    def run(self):
        count = 0
        while True:
            time.sleep(2)
            # print('this is thread in sub process')
            self.q.put(count)
            count += 1
            print('count:', count)


if __name__ == '__main__':
    p = Process(target=proc2) # 如果没有队列的话，宿主机和docker里面运行是一样的
    p.start()
    _main()
