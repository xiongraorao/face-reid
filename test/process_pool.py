# 进程池测试
import os
from multiprocessing import Process, Pool
import time

pool = {}

def run(t):
    time.sleep(t)
    print('over', os.getpid())

if __name__ == '__main__':
    p1 = Process(target=run, args=(3,))
    p2 = Process(target=run, args=(5,))
    p1.start()
    p2.start()

    pool[1] = p1
    pool[2] = p2
    time.sleep(2)
    for k,v in pool.items():
        print('process ', k , ' status : ', v.is_alive())



