import json
import os
import sys

import numpy as np
from sklearn.cluster import AffinityPropagation, MeanShift, estimate_bandwidth, DBSCAN
from sklearn.cluster import Birch

# get current file dir
sup = os.path.dirname(os.path.realpath(__file__))
sup = os.path.dirname(sup)
if sup not in sys.path:
    sys.path.append(sup)

from util import Mysql


def load_index(path):
    vectors = []
    with open(path, 'r') as f:
        for line in f:
            vector = json.loads(line.strip())['vector']
            vectors.append(vector)
    return vectors

def write_db(labels):
    # 写入数据库
    db = Mysql('192.168.1.11', 3306, 'root', '123456', 'face_reid')
    sql = "update t_cluster2 set cluster_id = %s where id = %s"
    for i, label in enumerate(labels):
        result = db.update(sql, (str(label), str(844 + i)))
        print(result)
    db.commit()

def ap(X):
    '''
    ap聚类方法，亲和力传播
    :return:
    '''

    # 计算X的相似度矩阵
    X = np.array(X)
    S = np.dot(X, X.T)
    print('avg: ', np.average(S))
    af = AffinityPropagation(affinity='precomputed', preference=-2).fit(S)
    cluster_center_indices = af.cluster_centers_indices_  # 聚类中心点
    labels = af.labels_  # 聚类之后的标签
    n_clusters = len(cluster_center_indices)  # 类别数量
    print('cluster_center_indices: ', cluster_center_indices)
    print('n_clusters', n_clusters)
    print('labels', labels)

    write_db(labels)


def meanshift(X):
    '''
    meanshift 聚类方法，适合密度均匀的
    :return:
    '''
    bandwidth = estimate_bandwidth(X, quantile=0.5, n_samples=20)
    ms = MeanShift(bandwidth=bandwidth, bin_seeding=True)
    ms.fit(X)
    labels = ms.labels_
    cluster_center = ms.cluster_centers_

    print('cluster_center: ', cluster_center)
    print('n_cluster: ', len(cluster_center))
    print('labels', labels)

    write_db(labels)


def dbscan(X):
    '''
    dbscan 聚类方法
    :return:
    '''
    db = DBSCAN(eps=0.6, min_samples=10, metric='cosine').fit(X)
    X = np.array(X)
    S = 1 - np.dot(X, X.T)
    db = DBSCAN(eps=0.6, min_samples=1, metric='precomputed').fit(S)

    labels = db.labels_
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise_ = list(labels).count(-1)
    print('n_clusters: ', n_clusters)
    print('n_noise: ', n_noise_)
    print('labels: ', labels)
    write_db(labels)
    print('db core sample index', len(db.core_sample_indices_))
    print('db algorithm', db.algorithm)
    return labels


def pca(X):
    '''
    主成分分析，对原始特征进行降维
    :return:
    '''
    from sklearn.decomposition import PCA
    X = load_index('./index-2018-12-26.log')
    pca = PCA(n_components=128)
    pca.fit(X)
    pca.transform()
    return pca.transform(X)


def llt(X):
    '''
    局部线性嵌入，用于降维
    :return:
    '''
    from sklearn import manifold
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D

    trans_data = manifold.LocallyLinearEmbedding(n_neighbors=30, n_components=3, method='standard').fit_transform(X)

    fig = plt.figure()
    ax = Axes3D(fig, elev=30, azim=-20)
    print(trans_data)
    ax.scatter(trans_data[:,0], trans_data[:, 1], trans_data[:, 2], marker='o', c='red')
    plt.show()


def birch(X):
    '''
    适合类别数较大的情况
    :return:
    '''
    labels = Birch(threshold=0.7, n_clusters=None).fit_predict(X)
    n_clusters = len(set(labels))
    print('n_clusters: ', n_clusters)
    print('labels: ', labels)
    write_db(labels)
    return labels


if __name__ == '__main__':
    X = load_index('./index-2018-12-26.log')
    # ap(X)
    # meanshift(X)
    dbscan(X)
    # birch(X)
    # llt(X)
    # data_transform = pca(X)
    # dbscan(data_transform)
