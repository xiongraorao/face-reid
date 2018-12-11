import asyncio

import time


async def async_add(a, b):
    # asyncio.sleep(1)
    c = 0
    while c < 1000000:
        c +=1
    return a + b


async def hello():
    print('Hello world: ', 'time=', time.time())
    r = await async_add(1, 3)  # 模拟做别的事情
    print('异步返回的结果：', r, 'time: ', time.time())


def run():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait([hello() for x in range(4)])) # 使用await是因为run_until_complete 是一个阻塞的函数


# run()

# 定义一个协程
async def add(a,b):
    asyncio.sleep(1)
    print('add result: ', a+b)
    return a+b

# 运行协程
def run2():
    start = time.time()
    loop = asyncio.get_event_loop()
    coroutine = add(1,2)
    result = loop.run_until_complete(coroutine)
    print('time: ', time.time() - start)
    print(result)

# run2()

# 定义一个task，用于获取协程结果
def run3():
    start = time.time()
    loop = asyncio.get_event_loop()
    coroutine = add(1,2)
    task = loop.create_task(coroutine) # 可以通过asyncio.ensure_future()来创建task
    print(task)
    loop.run_until_complete(task)
    print('time: ', time.time() - start)
    print(task.result())
run3()

def callback(future):
    print('callback: ', future.result())

# 绑定回调，用于获取返回的结果
def run4():
    start = time.time()
    loop = asyncio.get_event_loop()
    loop2 = asyncio.get_event_loop()
    print('id diff: ', id(loop), id(loop2)) # 同一个线程占有相同的内存空间
    coroutine = add(1,2)
    #task = loop.create_task(coroutine) # 可以通过asyncio.ensure_future()来创建task
    task = asyncio.ensure_future(coroutine, loop=loop) # loop 是线程特定，因此可以不用传递
    print(task)
    task.add_done_callback(callback)
    loop.run_until_complete(task)
    print('time: ', time.time() - start)
# run4()

# 阻塞和await
# await可以针对耗时的操作进行挂起， 例如hello协程

# 环很多时候，我们的事件循环用于注册协程，而有的协程需要动态的添加到事件循环中。
# 一个简单的方式就是使用多线程。当前线程创建一个事件循环，然后在新建一个线程，在新线程中启动事件循环。
# 当前线程不会被block。

def run5():
    from threading import Thread
    def start_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def more_work(x):
        print('More work {}'.format(x))
        time.sleep(x)
        print('Finished more work {}'.format(x))

    start = time.time()
    new_loop = asyncio.new_event_loop()
    t = Thread(target=start_loop, args=(new_loop,))
    t.start()
    print('TIME: {}'.format(time.time() - start))

    new_loop.call_soon_threadsafe(more_work, 6)
    new_loop.call_soon_threadsafe(more_work, 3)

    #启动上述代码之后，当前线程不会被block，新线程中会按照顺序执行call_soon_threadsafe方法注册
    # 的more_work方法， 后者因为time.sleep操作是同步阻塞的，因此运行完毕more_work需要大致6 + 3

# 参考文档：http://www.cnblogs.com/zhaof/p/8490045.html

def run6():
    now = lambda: time.time()

    async def do_some_work(x):
        print("waiting:", x)
        await asyncio.sleep(x)
        return "Done after {}s".format(x)

    async def main():
        coroutine1 = do_some_work(1)
        coroutine2 = do_some_work(2)
        coroutine3 = do_some_work(4)
        tasks = [
            asyncio.ensure_future(coroutine1),
            asyncio.ensure_future(coroutine2),
            asyncio.ensure_future(coroutine3)
        ]

        dones, pendings = await asyncio.wait(tasks)
        for task in dones:
            print("Task ret:", task.result())

        results = await asyncio.gather(*tasks)
        for result in results:
            print("Task ret:",result)

    start = now()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print("Time:", now() - start)

# run6()