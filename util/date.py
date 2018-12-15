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