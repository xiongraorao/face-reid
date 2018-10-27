import redis
import json


def redis_connect():
    pool = redis.ConnectionPool(host='192.168.1.11', port=6379, db=5)
    r = redis.Redis(connection_pool=pool)
    return r

r = redis_connect()
# r.sadd(4, "hello")
# r.sadd(4,'world')
# r.sadd(4,', today is a nice day')
r.set('name', '{"age":12,"sex":"male"}')

# keys = r.keys('*')
# for key in keys:
# s = r.smembers(key)
# for ss in s:
#     print(ss.decode('utf-8'))
print(r.get('name').decode('utf-8'))

# d = {'vector': [x for x in range(0, 256)], 'c_name': 'test'}
# r.set('F:\\datasets\\lfw\\Aaron_Guiel\\Aaron_Guiel_0001.jpg', json.dumps(d))
c = r.get('F:\\datasets\\lfw\\Aaron_Tippin\\Aaron_Tippin_0001.jpg')
print(c.decode('utf-8'))

keys = r.keys('*')
clusters = {}
for idx, key in enumerate(keys):
    value = json.loads(r.get(key).decode('utf-8'))
    key = key.decode('utf-8')
    if value['c_name'] in clusters.keys():
        clusters[value['c_name']].append(key)
    else:
        clusters[value['c_name']] = [key]
    if idx > 100:
        break

for key, val in clusters.items():
    print('cluster_name: ', key)
    print('samples: ')
    for v in val:
        print(v)
    print('===================')
