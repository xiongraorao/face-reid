import base64
import json

import requests

base_url = 'http://192.168.1.6:5000'
headers = {'content-type': "application/json"}

def search1_test():
    url = base_url + '/search/all'
    img = open('../img/oliver.jpg', 'rb')
    b64 = base64.b64encode(img.read()).decode('utf-8')
    data = {'image_base64': b64, 'start_pos': 0, 'limit': 100, 'query_id': 1545698649}
    # data = {'image_base64': b64, 'start_pos': 0, 'limit': 100}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response.json()


def freq_test():
    url = base_url + '/freq'
    data = {'start': '2018-12-19 10:00:00', 'end': '2019-12-21 19:00:00', 'start_pos': 0, 'limit': 100, 'cluster_id': '892202892012283969', 'freq':3}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response.json()

def trace_test():
    url = base_url + '/trace'
    data = {'start': '2018-12-19 10:00:00', 'end': '2019-12-21 19:00:00', 'start_pos': 0, 'limit': 100, 'cluster_id': '892202892012283969'}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response.json()

def peer_test():
    url = base_url + '/peer'
    data = {'query_id': 1545699125, 'start': '2019-12-19 10:00:00', 'end': '2019-12-21 19:00:00', 'gap': 10, 'min_times': 3, 'threshold': 0.1, 'start_pos': 0, 'limit': 100, 'cluster_id': '892202892012283969'}
    # data = {'start': '2018-12-19 10:00:00', 'end': '2019-12-21 19:00:00', 'gap': 10, 'min_times': 3, 'threshold': 0.1, 'start_pos': 0, 'limit': 100, 'cluster_id': '892202892012283969'}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response.json()

def repo_add():
    url = base_url + '/repository/add'
    data = {'name': 'ArrowMan'}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response.json()

def repo_del(id):
    url = base_url + '/repository/del'
    data = {'id': id}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response.json()

def repo_update(id, name):
    url = base_url + '/repository/update'
    data = {'id': id, 'name': name}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response.json()

def repos():
    url = base_url + '/repository/repos'
    response = requests.get(url, headers=headers)
    return response.json()

def picture_add():
    '''
    batch url add
    :return:
    '''
    url = base_url + '/repository/picture/batch_uri'
    data = {'repository_id': 8, 'path': '/home/xrr/test_dir'}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response.json()

def picture_add2():
    '''
    base64 导入
    :return:
    '''
    url = base_url + '/repository/picture/batch_image'
    data = {'repository_id': 8}
    imgs = ['F:\\oliver.jpg', 'F:\\digger.jpg']
    images = []
    for img in imgs:
        f = open(img, 'rb')
        b64 = base64.b64encode(f.read()).decode('utf-8')
        image = {'image_base64': b64, 'person_id': img[:-4]}
        images.append(image)
    data['images'] = images
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response.json()


def contact_test():
    url = base_url + '/repository/test'
    response = requests.get(url)
    return response.text

def search2_test():
    url = base_url + '/search/repos'
    data = {'repository_ids': [8], 'start_pos': 0, 'limit': 100}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response.json()

def search3_test():
    url = base_url + '/search/libs'
    img = open('../img/oliver.jpg', 'rb')
    b64 = base64.b64encode(img.read()).decode('utf-8')
    data = {'image_base64': b64, 'start_pos': 0, 'limit': 100}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response.json()

if __name__ == '__main__':
    # result = search1_test()

    # result = freq_test()

    # result = trace_test()

    # result = peer_test()

    # result = repo_add()

    # result = repo_del(4)

    # result = repo_update(5, 'arrowman')

    # result = repos()

    # result = picture_add()

    # result = contact_test()

    # result = picture_add2()

    # result = search2_test()

    result = search3_test()

    print(json.dumps(result))




    # img = open('../img/oliver.jpg', 'rb')
    # b64 = base64.b64encode(img.read()).decode('utf-8')
    # face_tool = Face('tcp://192.168.1.11:5559')
    # feature = face_tool.feature(b64)
    # print(feature)

    # # 验证
    # img = open('../img/felicity.jpg', 'rb')
    # b64 = base64.b64encode(img.read()).decode('utf-8')
    # face_tool = Face('tcp://192.168.1.11:5559')
    # feature = face_tool.feature(b64)
    #
    # b642 = get_as_base64('http://192.168.1.6:38080/4,0533803af009')
    # feature2 = face_tool.feature(b642)
    #
    # import numpy as np
    # sim = np.dot(feature, feature2)
    # print(sim)

    # t = time.time()
    # dt = datetime.datetime.fromtimestamp(t)
    # x = dt.strftime('%Y-%m-%d %H:%M:%S')
    # print(type(x))

##
import re
pattern = re.compile('0[0-9]:[0-5][0-9]:[0-5][0-9]|1[0-9]:[0-5][0-9]:[0-5][0-9]|2[0-3]:[0-5][0-9]:[0-5][0-9]')
##