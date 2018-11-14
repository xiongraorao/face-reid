from multiprocessing import Process, Queue, Pipe
import time, random

def produce(q):
    count = 0
    while True:
        time.sleep(random.random() * 3)
        if q.full() is False:
            val = count * count
            print('produce product: ', val)
            q.put(val)
        count += 1

def consume(q):
    while True:
        time.sleep(random.random()*3)
        if q.empty() is False:
            print('consume product: ', q.get())
        else:
            print('q is empty')
            continue

def proc1(conn):
    for i in range(10):
        conn.send(i)
        print('send {} to pipe '.format(i))
        time.sleep(1)
def proc2(conn):
    n = 9
    while n > 0:
        result = conn.recv()
        print('receive {} from pip'.format(result))
        n -= 1

if __name__ == '__main__':
    q = Queue(20)
    proc_produce = Process(target=produce, args=(q,))
    proc_consume = Process(target=consume, args=(q,))
    proc_produce.start()
    proc_consume.start()

    p1, p2 = Pipe(True) # True 表示两个管道是全双工的，均可收发
    process1 = Process(target=proc1, args=(p1,))
    process2 = Process(target=proc2, args=(p2,))
    process1.start()
    process2.start()
    process1.join()
    process2.join()
    p1.close()
    p2.close()
    print('end')