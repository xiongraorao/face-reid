import time
# from mysql import Mysql
# from logger import Log

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

# if __name__ == '__main__':
#     # 1.test
#     now = round(time.time())
#     print(now)
#     date = time_to_date(now)
#     print(date)
#     t = date_to_time(date)
#     print(t)
#
#     # 2. mysql 测试
#     db = Mysql(host='192.168.1.11',port=3306,user='root',password='123456',db='face_reid')
#     logger = Log('date', is_save=False)
#     db.set_logger(logger)
#     # sql = "insert into `t_test` (time) values (%s)"
#     # ret = db.insert(sql, (time_to_date(round(time.time()))))
#     # db.commit()
#     # print(ret)
#
#     sql = "select time from `t_test` where id = %s"
#     result = db.select(sql, 2)
#     print(result[0][0])

# test = '2018-09-08 19:00:10'
# # timestamp = date_to_time(test)
# timeArray = time.strptime(test, "%Y-%m-%d %H:%M:%S")
# # print(timestamp)


