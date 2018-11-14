import threading
import time


def show(msg):
    time.sleep(1)
    print('thread name = %s, msg = %s' % (threading.current_thread().name, msg))


class MyThread(threading.Thread):
    def __init__(self, arg):
        super(MyThread, self).__init__()  # 注意：一定要显式的调用父类的初始化函数。
        self.arg = arg

    def run(self):  # 定义每个线程要运行的函数
        time.sleep(1)
        print('the arg is:%s\r' % self.arg)
t1 = threading.Thread(target=show, args=('hello',))
t2 = MyThread('hello')
t1.start()
t2.start()
print('this is main thread, name = %s' % threading.current_thread().name)
