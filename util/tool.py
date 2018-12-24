import time


def time_to_date(timestamp):
    '''
    时间戳转换成mysql的Date类型的时间
    :return:
    '''
    timeArray = time.localtime(timestamp)
    format = "%Y-%m-%d %H:%M:%S"
    return time.strftime(format, timeArray)

def date_to_time(date):
    '''
    mysql 的Date类型的时间转化成时间戳
    :param date:
    :return:
    '''
    timeArray = time.strptime(date, "%Y-%m-%d %H:%M:%S")
    timestamp = int(time.mktime(timeArray))
    return timestamp

def trans_sqlin(x):
    '''
    把list、tuple转换成sql中的in 后面的集合
    eg: [1,2,3] ==> (1,2,3)
        [1] ==> (1)
        [] ==> (null)
    :return:
    '''
    if x is None or len(x) == 0:
        return '(null)'
    elif len(x) == 1:
        return '(%s)'%(x[0])
    else:
        return str(tuple(x))

def trans_sqlinsert(x):
    '''
    把二维的list, tuple 转换成sql中的values 后面的东西
    :param x:
    :return:
    '''
    if x is None or len(x) == 0:
        return None
    elif len(x) == 1:
        x = tuple(map(lambda a:tuple(a), x))
        return str(tuple(x))[1:-2]
    else:
        x = tuple(map(lambda a:tuple(a), x))
        return str(tuple(x))[1:-1]