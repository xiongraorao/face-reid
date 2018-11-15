import threading

summary = 0

lock = threading.Lock()


def add():
    global summary
    # global lock
    lock.acquire()
    for i in range(100000):
        summary += 1
        summary -= 1
    lock.release()


def start():
    for t in range(100):
        t = threading.Thread(target=add)
        t.start()
    print('summary = ', summary)


start()
