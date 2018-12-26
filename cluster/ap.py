import json
import os
import sys

import numpy as np
from sklearn.cluster import AffinityPropagation

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


def __main():
    '''
    ap聚类方法
    :return:
    '''
    X = load_index('./index-2018-12-26.log')

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

    # 写入数据库
    db = Mysql('192.168.1.11', 3306, 'root', '123456', 'face_reid')
    sql = "update t_cluster2 set cluster_id = %s where id = %s"
    for i, label in enumerate(labels):
        result = db.update(sql, (str(label), str(844 + i)))
        print(result)
    db.commit()


if __name__ == '__main__':
    __main()
