import os
import subprocess as sp


def test():
    print('Process (%s) start...' % os.getpid())
    pid = os.fork()
    if pid == 0:
        print('this is child process (%s) , parent = %s' % (os.getpid(), os.getppid()))
    else:
        print('I (%s) just created a child process (%s)' % (os.getpid(), pid))


def sub_proc1():
    out = os.popen('ping www.baidu.com -c 5')
    print(out.read())


def sub_proc2():
    print('start subprocess')
    p = sp.Popen(['nslookup'], stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    out, err = p.communicate(bytes('www.baidu.com', encoding='utf-8'))
    print(out.decode('utf-8'))
    print('exit')

def sub_proc3():
    print('start subProcess')

if __name__ == '__main__':
    sub_proc1()
    sub_proc2()
    sub_proc2()
