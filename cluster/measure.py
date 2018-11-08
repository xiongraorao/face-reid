'''
this file is to measure the clustering result.
'''

import math
import sys

import numpy as np


class Sample(object):
    def __init__(self, name, vector, c_name=None, ped_vector= []):
        self.name = name  # 样本点的名字
        self.vector = vector  # 样本点的特征向量
        self.c_name = c_name  # 样本所属类名
        self.ped_vector = ped_vector


class Cluster(object):
    def __init__(self, name, samples):
        self.name = name  # 类名
        self.samples = samples  #


def sample_2_json(obj):
    return {
        'name': obj.name,
        'vector': obj.vector,
        'c_name': obj.c_name
    }


def cen(c1, c2):
    '''
    求两个类簇的中心点的距离
    :param c1:
    :param c2:
    :return:
    '''
    # v1, v2 = 0, 0
    # for s in c1.samples:
    #     v1 += np.array(s.vector, dtype=float)
    # for s in c2.samples:
    #     v2 += np.array(s.vector, dtype=float)
    # v1 = v1 / len(c1.samples)
    # v2 = v2 / len(c2.samples)
    # dis = v1.dot(v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    # vectorization
    v1, v2 = 0, 0
    if len(c1.samples) == 0 or len(c2.samples) == 0:
        return 0.0
    v1 = np.array([x.vector for x in c1.samples]).reshape(len(c1.samples), -1)  # c1.len * vector_dim(256)
    v1 = np.average(v1, axis=0)
    v2 = np.array([x.vector for x in c2.samples]).reshape(len(c2.samples), -1)  # c2.len * vector_dim(256)
    v2 = np.average(v2, axis=0)
    dis = v1.dot(v2)
    return 1 - dis


def avg(cluster):
    '''
    求簇cluster的样本间的平均距离
    :param cluster: Cluster
    :return: 平均距离
    '''
    # samples = cluster.samples
    # C = len(samples)
    # sum = 0
    # if C <= 1:
    #     return 0
    # for i in range(0, C):
    #     for j in range(i + 1, C):
    #         vi = np.array(samples[i].vector, dtype=float)
    #         vj = np.array(samples[j].vector, dtype=float)
    #         ## 计算cosine
    #         cos = vi.dot(vj) / (np.linalg.norm(vi) * np.linalg.norm(vj))
    #         sum += 1 - cos
    # avg = 2 / (C * (C - 1)) * sum

    # vectorization
    samples = cluster.samples
    C = len(samples)
    if C <= 1:
        return 0
    a = np.array([x.vector for x in samples]).reshape(C, -1).T  # vector_dim(256) * samples.len
    a = np.expand_dims(a, axis=-1)
    a = a.repeat(C, axis=-1)  # a.shape: 256*C*C
    # cos = np.sum(a*a, axis=0) # ret: C*C，下面是一步到位的
    cos = (np.sum(a * a) - C) / 2
    sum = C * (C - 1) / 2 - cos
    avg = 2 / (C * (C - 1)) * sum
    return avg


def min_c(c1, c2):
    '''
    计算两个类簇中最近样本的距离
    :param c1:
    :param c2:
    :return:
    '''
    # min_dist = sys.maxsize
    # for s1 in c1.samples:
    #     for s2 in c2.samples:
    #         vi = np.array(s1.vector, dtype=float)
    #         vj = np.array(s2.vector, dtype=float)
    #         dist = 1 - vi.dot(vj) / (np.linalg.norm(vi) * np.linalg.norm(vj))
    #         min_dist = dist if min_dist > dist else min_dist

    # vectorization
    s1 = np.array([x.vector for x in c1.samples]).reshape(len(c1.samples), -1).T # 256*C
    s2 = np.array([x.vector for x in c2.samples]).reshape(len(c2.samples), -1).T # 256*C
    s1 = np.expand_dims(s1, axis=-1) # 256*C*1
    s1 = np.repeat(s1, len(c1.samples), axis=-1) # 256*C*C
    s2 = np.expand_dims(s2, axis=-1)
    s2 = np.repeat(s2, len(c2.samples), axis=-1) # 256*C*C
    s = np.max(s1*s2, axis=0)
    s = 1 - s
    return s


def max_diam(clusters):
    '''
    :param clusters: 等待计算的所有类簇
    :return:
    '''
    max = -1
    k = len(clusters)
    for i in range(0, k):
        temp = diam(clusters[i])
        max = temp if temp > max else max
    return max


def diam(c):
    '''
    簇C内样本最远的距离
    :param c:
    :return:
    '''
    # samples = c.samples
    # C = len(samples)
    # max = -1
    # for si in range(0, C):
    #     for sj in range(si + 1, C):
    #         vi = np.array(samples[si].vector, dtype=float)
    #         vj = np.array(samples[sj].vector, dtype=float)
    #         dist = 1 - vi.dot(vj) / (np.linalg.norm(vi) * np.linalg.norm(vj))
    #         if max < dist:
    #             max = dist

    # vectorization
    samples = c.samples
    C = len(samples)
    if C <= 1:
        return 0
    a = np.array([x.vector for x in samples]).reshape(-1, C)
    a = np.expand_dims(a, axis=-1)
    a = a.repeat(C, axis=-1)
    cos = np.sum(a * a, axis=0)  # cos: C*C
    max = 1 - np.min(cos)
    return max


def __pre(clusters1, clusters2):
    """
    :param clusters1: 标准类簇(GroundTruth)
    :param clusters2:  聚类簇(Cluster)
    :return: a, b, c, d
    """
    c1 = {}
    c2 = {}
    for cluster in clusters1:
        for s in cluster.samples:
            c1[s.name] = s.c_name  # dict: sample_name -> cluster_name
    for cluster in clusters2:
        for s in cluster.samples:
            c2[s.name] = s.c_name  # dict: sample_name -> cluster_name

    # 统计数量
    a, b, c, d = 0, 0, 0, 0

    # 对cluster进行排序操作,得到簇标记向量
    c1 = [c1.get(k) for k in sorted(c1.keys())]
    c2 = [c2.get(k) for k in sorted(c2.keys())]
    if len(c1) != len(c2):
        print('ground truth and predict cluster should have same size')
        exit(0)
    for i in range(0, len(c1)):
        for j in range(i + 1, len(c2)):
            if c1[i] == c1[j] and c2[i] == c2[j]:
                a += 1
            elif c1[i] == c1[j] and c2[i] != c2[j]:
                b += 1
            elif c1[i] != c1[j] and c2[i] == c2[j]:
                c += 1
            else:
                d += 1

    return a, b, c, d, len(c1)


def __pre2(clusters1, clusters2):
    '''
    采用向量化的计算方法计算
    :param clusters1: 标准类簇(GroundTruth)
    :param clusters2:  聚类簇(Cluster)
    :return:
    '''
    c1 = {}
    c2 = {}
    for cluster in clusters1:
        for s in cluster.samples:
            c1[s.name] = s.c_name  # dict: sample_name -> cluster_name
    for cluster in clusters2:
        for s in cluster.samples:
            c2[s.name] = s.c_name  # dict: sample_name -> cluster_name

    # 统计数量
    a, b, c, d = 0, 0, 0, 0

    # 对cluster进行排序操作,得到簇标记向量
    c1 = [c1.get(k) for k in sorted(c1.keys())]
    c2 = [c2.get(k) for k in sorted(c2.keys())]

    # 构建一个二维数组,每个cell为（x,y) 判断x,y满足的条件即可
    if len(c1) != len(c2):
        print('ground truth and predict cluster should have same size')
        exit(0)
    n = len(c1)
    c1 = np.array(c1).reshape(1, -1)
    c2 = np.array(c2).reshape(1, -1)
    c1_0 = np.repeat(c1, n, axis=0)
    c1_1 = np.repeat(c1.reshape(-1, 1), n, axis=1)
    c2_0 = np.repeat(c2, n, axis=0)
    c2_1 = np.repeat(c2.reshape(-1, 1), n, axis=1)

    temp = (c1_0 == c1_1) & (c2_0 == c2_1)
    a = (np.sum(temp) - np.trace(temp)) / 2
    temp = (c1_0 == c1_1) & (c2_0 != c2_1)
    b = (np.sum(temp) - np.trace(temp)) / 2
    temp = (c1_0 != c1_1) & (c2_0 == c2_1)
    c = (np.sum(temp) - np.trace(temp)) / 2
    temp = (c1_0 != c1_1) & (c2_0 != c2_1)
    d = (np.sum(temp) - np.trace(temp)) / 2
    assert a + b + c + d == n * (n - 1) / 2
    print('a=%d, b=%d, c=%d, d=%d' % (a, b, c, d))
    return a, b, c, d, n


def inner_index(clusters1, clusters2):
    '''
    内部性能度量标准, 三个指数越大越好（0-1）之间
    :param clusters1:
    :param clusters2:
    :return: 内部性能指数
    '''
    a, b, c, d, m = __pre2(clusters1, clusters2)
    jaccard = float(a / (a + b + c))
    fmi = math.sqrt(float(a / (a + b)) * float(a / (a + c)))
    ri = float(2 * (a + d) / (m * (m - 1)))
    return jaccard, fmi, ri


def outer_index(clusters):
    '''
    外部性能度量标准,
    :param clusters： 聚类的结果
    :return: 外部性能指数， DBI 和DI指数， DBI越小越好，DI越大越好
    '''

    # 得到簇划分
    c = []
    for cluster in clusters:
        for s in cluster.samples:
            c.append(s.c_name)

    # 计算参数
    k = len(clusters)  # 簇的个数

    DBI = 0
    for i in range(0, k):
        max = -1
        for j in range(0, k):
            if i == j:
                continue
            temp = (avg(clusters[i]) + avg(clusters[j])) / cen(clusters[i], clusters[j])
            if max < temp:
                max = temp
        DBI += max
    DBI = DBI / k

    # DI = sys.maxsize
    # for i in range(0, k):
    #     temp_min = sys.maxsize
    #     for j in range(i + 1, k):
    #         temp = min_c(clusters[i], clusters[j]) / max_diam(clusters)
    #         temp_min = temp if temp < temp_min else temp_min
    #     DI = temp_min if temp_min < DI else DI
    # DI = 0

    return DBI
