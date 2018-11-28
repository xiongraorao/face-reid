import json

import requests

from config import search_host, search_port

headers = {'content-type': "application/json"}
base_url = 'http://' + search_host + ':' + str(search_port)


def add(ids, nparray):
    '''
    添加索引
    :param ids: 向量唯一的标识， unsigned int
    :param nparray: 二维向量，每行为一个vector
    :return:
    '''
    url = base_url + '/add'
    print(url)
    n = nparray.shape[0]
    if len(ids) != n:
        print('parameters error!')
        return
    data = {}
    for i in range(n):
        data[ids[i]] = nparray[i, :].tolist()
    data_request = {'ntotal': n, 'data': data}
    response = requests.post(url, data=json.dumps(data_request), headers=headers)
    text = response.json()
    # print(text)
    return text


def search(topk, queries):
    '''
    批量搜索
    :param qtotal:
    :param topk:
    :param queries:
    :return:
    '''
    url = base_url + '/search'
    data = {}
    qtotal = queries.shape[0]
    q = {}
    for i in range(qtotal):
        q[i] = queries[i, :].tolist()
    data_request = {'qtotal': qtotal, 'topk': topk, 'queries': q}
    response = requests.post(url, data=json.dumps(data_request), headers=headers)
    text = response.json()
    # print(text)
    return text


def delete(ids):
    '''
    删除向量
    :param ids: 向量的唯一标识, list
    :return:
    '''
    url = base_url + '/delete'
    response = requests.post(url, data=json.dumps({'ids': ids}), headers=headers)
    text = response.json()
    # print(text)
    return text


def deleteRange(start, end):
    '''
    按照id的范围删除
    :param start: int
    :param end: int 
    :return:
    '''
    url = base_url + '/deleteRange'
    data_request = json.dumps({'start': start, 'end': end})
    response = requests.post(url, data=data_request, headers=headers)
    text = json.loads(response.text)
    print(text)
    return text


def reconfig(path):
    '''
    重新配置和加载索引文件
    :param path: config path
    :return:
    '''
    url = base_url + '/reconfig'
    data_request = json.dumps({'reconfigFilePath': path})
    response = requests.post(url, data=data_request, headers=headers)
    text = json.loads(response.text)
    # print(text)
    return text


def searchRange(nq, radius, queries):
    '''
    查询范围内向量
    :param nq: 需要查询的向量个数
    :param radius: 查询最近邻的范围阈值
    :param queries: 需要查询的向量标识和对应的特征向量
    :return:
    '''
    url = base_url + '/searchRange'
    data_request = {'nq': nq, 'radius': radius}
    q = {}
    for i in range(nq):
        q[i] = queries[i, :].tolist()
    data_request['queries'] = q
    data_request = json.dumps(data_request)
    response = requests.post(url, data=data_request, headers=headers)
    text = response.json()  # json.loads(response.text)
    # print(text)
    return text
