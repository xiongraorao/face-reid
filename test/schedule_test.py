'''
测试定时任务调度
'''
import schedule
import time
from threading import Lock, Thread, Condition
cond = Condition()

def job():
    global cond
    cond.acquire()
    print('hello world')
    cond.wait(3)
    cond.release()

def main():
    global cond
    cond.acquire()
    print('main thread')
    time.sleep(2)
    print('main over')
    cond.notify()
    cond.release()

schedule.every().seconds.do(job)


while True:
    main()
    job()
# while True:
#     schedule.run_pending()

