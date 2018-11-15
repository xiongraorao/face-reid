import threading
import queue
import time
import os

lock = threading.RLock()


def produce(q):
    '''
    向消息队列里面写数据
    :param q:
    :return:
    '''
    count = 0
    print('pid = ', os.getpid())
    while True:
        pass
        # time.sleep(0.001)
        # q.put(count)
        # print('produce: ', count)
        # count += 1


if __name__ == '__main__':
    q = queue.Queue()
    t = threading.Thread(target=produce, args=(q,))
    t.start()
