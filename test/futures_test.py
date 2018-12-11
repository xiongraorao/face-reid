import time
from concurrent import futures


def run(a, b, c):
    time.sleep(c)
    return a + b


def foo1():
    pool = futures.ThreadPoolExecutor(5)
    a = pool.submit(run, 1, 2, 3)
    print('current time:', time.time())
    b = pool.submit(run, 3, 4, 1)
    print('current time:', time.time())

    # try:
    #     result = a.result(2)
    #     print(result)
    # except TimeoutError as e:
    #     print('3 secondes has gone, task1 has not complete, break')
    #     print(e)

    while b.running():
        print('task2 has been running')
        print('wait 1 second')
        time.sleep(1)

    if a.done():
        print('task1 has done, result:', a.result())

    if b.done():
        print('task2 has done, result:', b.result())

    print(a, b)

foo1()
