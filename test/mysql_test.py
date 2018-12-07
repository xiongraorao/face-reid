from util.mysql import Mysql
from util.logger import Log

host='192.168.1.11'
port=3306
user='root'
password='123456'
db='face_reid'
charset='utf8'

logger = Log(__name__,is_save=False)

db = Mysql(host, port, user, password, db, charset)
db.set_logger(logger)

sql = "insert into `t_camera` (`name`, `url`, `rate`, `grab`) values (%s, %s, %s, %s)"

db.insert(sql, ('test1', 'rtsp1', 10,10))
db.commit()
# db.insert(sql, ('test2', 'rtsp2', 20,20))

sql = "select `url` from `t_camera` where id = %s"

db.truncate('t_camera')

data = db.select(sql, 2)

print(data[0][0])
