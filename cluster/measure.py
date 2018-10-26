'''
this file is to measure the clustering result.
'''

import math
import sys

import numpy as np


def cen(c1, c2):
    '''
    求两个类簇的中心点的距离
    :param c1:
    :param c2:
    :return:
    '''
    v1, v2 = 0, 0
    for s in c1.samples:
        v1 += np.array(s.vector, dtype=float)
    for s in c2.samples:
        v2 += np.array(s.vector, dtype=float)
    v1 = v1 / len(c1.samples)
    v2 = v2 / len(c2.samples)
    dis = v1.dot(v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    return 1 - dis


def avg(cluster):
    '''
    求簇cluster的样本间的平均距离
    :param cluster: Cluster
    :return: 平均距离
    '''
    C = len(cluster.samples)
    sum = 0
    for i in range(0, C):
        for j in range(i + 1, C):
            if i >= j:
                continue
            vi = np.array(cluster[i].vector, dtype=float)
            vj = np.array(cluster[j].vector, dtype=float)
            ## 计算cosine
            cos = vi.dot(vj) / (np.linalg.norm(vi) * np.linalg.norm(vj))
            sum += 1 - cos
    avg = 2 / (C * (C - 1)) * sum
    return avg


class Sample(object):
    def __init__(self, name, vector, c_name=None):
        self.name = name  # 样本点的名字
        self.vector = vector  # 样本点的特征向量
        self.c_name = c_name  # 样本所属类名


class Cluster(object):
    def __init__(self, name, samples):
        self.name = name  # 类名
        self.samples = samples  # 样本点的集合

    def __pre(self, clusters1, clusters2):

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

        for i in range(0, len(c1)):
            for j in range(i + 1, len(c2)):
                if i >= j:
                    continue
                if c1[i] == c1[j] and c2[i] == c2[j]:
                    a += 1
                elif c1[i] == c1[j] and c2[i] != c2[j]:
                    b += 1
                elif c1[i] != c1[j] and c2[i] == c2[j]:
                    c += 1
                else:
                    c += 1

        return a, b, c, d

    def inner_index(self, clusters1, clusters2):
        '''
        内部性能度量标准, 三个指数越大越好（0-1）之间
        :param clusters1:
        :param clusters2:
        :return: 内部性能指数
        '''
        if len(clusters1) != len(clusters2):
            print('cluster1 and cluster2 has not same length')
            exit(0)
        a, b, c, d = self.__pre(self, clusters1, clusters2)
        m = len(clusters1)
        jaccard = float(a / (a + b + c))
        fmi = math.sqrt(float(a / (a + b)) * float(a / (a + c)))
        ri = float(2 * (a + d) / (m * (m - 1)))
        return jaccard, fmi, ri

    def outer_index(self, clusters):
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

        DI = sys.maxsize
        for i in range(0, k):
            temp_min = sys.maxsize
            for j in range(i + 1, k):
                temp = min_c(clusters[i], clusters[j]) / max_diam(clusters)
                temp_min = temp if temp < temp_min else temp_min
            DI = temp_min if temp_min < DI else DI

        return DBI, DI


def min_c(c1, c2):
    '''
    计算两个类簇中最近样本的距离
    :param c1:
    :param c2:
    :return:
    '''
    min_dist = sys.maxsize
    for s1 in c1.samples:
        for s2 in c2.samples:
            vi = np.array(s1.vector, dtype=float)
            vj = np.array(s2.vector, dtype=float)
            dist = 1 - vi.dot(vj) / (np.linalg.norm(vi) * np.linalg.norm(vj))
            min_dist = dist if min_dist > dist else min_dist
    return min_dist


def max_diam(clusters):
    '''
    :param clusters: 等待计算的所有类簇
    :return:
    '''
    max = -1
    k = len(clusters)
    for i in (0, k):
        temp = diam(clusters[i])
        max = temp if temp > max else max
    return max


def diam(c):
    '''
    簇C内样本最远的距离
    :param c:
    :return:
    '''
    C = len(c.samples)
    max = -1
    for si in range(0, C):
        for sj in range(si + 1, C):
            vi = np.array(si.vector, dtype=float)
            vj = np.array(sj.vector, dtype=float)
            dist = 1 - vi.dot(vj) / (np.linalg.norm(vi) * np.linalg.norm(vj))
            if max < dist:
                max = dist
    return max
