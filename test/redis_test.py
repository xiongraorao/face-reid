import redis

def redis_connect():
    pool = redis.ConnectionPool(host='192.168.1.11', port=6379, db=5)
    r = redis.Redis(connection_pool=pool)
    return r

r = redis_connect()
r.sadd(4, "hello")
r.sadd(4,'world')
r.sadd(4,', today is a nice day')

keys = r.keys('*')
for key in keys:
    s = r.smembers(key)
    for ss in s:
        print(ss)