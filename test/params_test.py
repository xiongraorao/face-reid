def foo(p1, *p2, **p3):
    print('p1: ', p1)
    print('p2: ', p2)
    print('p3: ', p3)
    print(set(p3))
    default = {
        'name' : 'xrr',
        'passwd' : 'test'
    }
    print(set(default))
    print(set(p3).difference(set(default)))

foo('sss', 'hello', 'word', 123, name='xrr', passwd = 'test', extra='extra_param')