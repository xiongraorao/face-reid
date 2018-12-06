# 进程池测试

from multiprocessing import Process, Pool
import time
from util.grab import Grab

def run(id):

    g = Grab()

p = Pool(4)
for i in range(4):
    p.apply_async(run, (i,))

if __name__ == '__main__':
    url = 'rtsp://admin:iec123456@192.168.1.72:554/unicast/c1/s0/live'


