from sklearn.cluster import DBSCAN


def dbscan(X, precomputed=False):
    '''
    dbscan 聚类方法
    :param X: 输入数据
    :return:
    '''
    if precomputed:
        labels = DBSCAN(eps=0.6, min_samples=10, metric='precomputed').fit_predict(X)
    else:
        labels = DBSCAN(eps=0.6, min_samples=10, metric='cosine').fit_predict(X)
    return labels

