'''
index test
'''

from util.search import Search
import numpy as np

searcher = Search('192.168.1.6', 2333)

nb = 10000
d = 256
ids = [a for a in range(nb)]
data = np.random.random((nb, d)).astype('float32')
features = data.tolist()

print('ok')

def add():
    ret = searcher.add(ids, features)
    print(ret)

def search():
    ret = searcher.search(5, [features[0], features[4], features[7]])
    print(ret)


if __name__ == '__main__':
    add()
    search()
