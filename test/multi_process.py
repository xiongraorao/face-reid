from multiprocessing import Process, Pool, Manager
import signal
import time
import os

def run(return_dict):
    '''
    子进程运行
    :return:
    '''
    print('child process pid: ', os.getpid())
    return_dict['pid'] = os.getpid()
    while True:
        print('running process! ')
        time.sleep(5)
        raise RuntimeError('test error')
ret_dict = Manager().dict()
try:
    p = Process(target=run, args=(ret_dict,))
    p.start()
    print('main process pid: ', os.getpid())
    time.sleep(2)
    print('main process, child process pid: ', ret_dict['pid'])
    time.sleep(10)
    p.terminate()
    print('begin kill process ',  ret_dict['pid'])
    os.kill(ret_dict['pid'],signal.SIGKILL)
    print('after kill process ',  ret_dict['pid'])
    print('over child process')
    time.sleep(50)
except RuntimeError as e:
    print(e)

#p.join()
#print('over')