from util.search import *
import numpy as np


if __name__ == '__main__':
    nb = 10000
    d = 256
    data = np.random.random((nb, d)).astype('float32')
    print(data)
    add(np.arange(nb).tolist(), data)
    #search(5, data[10:15, :])
    #delete(np.array([1, 3, 5, 7, 8, 12]).tolist())
    #deleteRange(0, 5)
    #searchRange(5, 0.5, data[10:15, :])
    #reconfig('config.json')

