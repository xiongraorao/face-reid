import time
def f():
    count = 0
    while True:
        yield count
        count += 1

a = f()
a.send(None)

while True:
    time.sleep(1)
    print(next(a))