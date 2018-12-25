import json

import requests

headers = {'content-type': "application/json"}


class Search():
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def add(self, ids, vectors):
        '''
        批量添加索引
        :param ids: 向量唯一的标识， unsigned int
        :param vectors: 二维向量，每行为一个vector
        :type list[list[]]
        :return:
        '''
        url = 'http://' + self.host + ':' + str(self.port) + '/add'
        n = len(vectors)
        if len(ids) != n:
            print('parameters error!')
            return
        data = {}
        for i in range(n):
            data[ids[i]] = vectors[i]
        data_request = {'ntotal': n, 'data': data}
        response = requests.post(url, data=json.dumps(data_request), headers=headers)
        text = response.json()
        return text

    def search(self, topk, queries):
        '''
        批量搜索
        :param qtotal:
        :param topk:
        :param queries:
        :return: queriers * topk 的二维数组
        '''
        url = 'http://' + self.host + ':' + str(self.port) + '/search'
        qtotal = len(queries)
        q = {}
        for i in range(qtotal):
            q[i] = queries[i]
        data_request = {'qtotal': qtotal, 'topk': topk, 'queries': q}
        response = requests.post(url, data=json.dumps(data_request), headers=headers)
        text = response.json()
        return text

    def delete(self, ids):
        '''
        删除向量
        :param ids: 向量的唯一标识, list
        :return:
        '''
        url = 'http://' + self.host + ':' + str(self.port) + '/delete'
        response = requests.post(url, data=json.dumps({'ids': ids}), headers=headers)
        text = response.json()
        return text

    def deleteRange(self, start, end):
        '''
        按照id的范围删除
        :param start: int
        :param end: int
        :return:
        '''
        url = 'http://' + self.host + ':' + str(self.port) + '/deleteRange'
        data_request = json.dumps({'start': start, 'end': end})
        response = requests.post(url, data=data_request, headers=headers)
        text = json.loads(response.text)
        return text

    def reconfig(self, path):
        '''
        清空索引
        :param path: config path
        :return:
        '''
        url = 'http://' + self.host + ':' + str(self.port) + '/reconfig'
        data_request = json.dumps({'reconfigFilePath': path})
        response = requests.post(url, data=data_request, headers=headers)
        text = json.loads(response.text)
        return text

    def searchRange(self, nq, radius, queries):
        '''
        查询范围内向量
        :param nq: 需要查询的向量个数
        :param radius: 查询最近邻的范围阈值
        :param queries: 需要查询的向量标识和对应的特征向量
        :return:
        '''
        url = 'http://' + self.host + ':' + str(self.port) + '/searchRange'
        data_request = {'nq': nq, 'radius': radius}
        q = {}
        for i in range(nq):
            q[i] = queries[i, :].tolist()
        data_request['queries'] = q
        data_request = json.dumps(data_request)
        response = requests.post(url, data=data_request, headers=headers)
        text = response.json()  # json.loads(response.text)
        return text

class Faiss():
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def add(self, ntotal, ids, vectors):
        '''
        添加向量到索引
        :param ntotal: 向量个数
        :param ids: 特征向量的id list
        :type list
        :param vectors: 特征向量的list
        :type list[list]
        :return:
        '''
        url = 'http://' + self.host + ':' + str(self.port) + '/add'
        data_request = {'ntotal': ntotal, 'data': {'ids': ids, 'vectors': vectors}}
        response = requests.post(url, data=json.dumps(data_request), headers=headers)
        return response.json()

    def search(self, qtotal, topk, queries):
        '''
        查询向量
        :param qtotal: 查询的向量个数
        :param topk: 查询topk个相似的向量
        :param queries: 查询向量的list
        :type list[list]
        :return:
        '''
        url = 'http://' + self.host + ':' + str(self.port) + '/search'
        data_request = {'qtotal':qtotal, 'topk': topk, 'queries': queries}
        response = requests.post(url, data=json.dumps(data_request), headers=headers)
        return response.json()

    def delete(self, ids):
        '''
        删除向量
        :param ids: 待删除向量的id 列表
        :type list
        :return:
        '''
        url = 'http://' + self.host + ':' + str(self.port) + '/del'
        data_request = {'ids': ids}
        response = requests.post(url, data=json.dumps(data_request), headers=headers)
        return response.json()