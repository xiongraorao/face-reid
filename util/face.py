#!/usr/bin/env python
# coding=utf-8

import base64
import json
import os
import requests
import cv2
import numpy as np
import zmq


class Face:
    x = 0
    y = 0
    width = 0
    height = 0
    sideFace = 0
    quality = 0
    score = 0


def get_list_files(path):
    ret = []
    for root, dirs, files in os.walk(path):
        for filespath in files:
            ret.append(os.path.join(root, filespath))
    return ret


def extract(base64):
    '''
    提取人脸
    {'status': 0, 'message': '成功获取到人脸特征', 'data': [0.02387029491364956, ..., 0.053947705775499344]}
    :param base64:
    :return:
    '''
    data_request = {'image_base64': base64}
    url = 'http://192.168.1.11:2313/faces/feature'
    headers = {'content-type': "application/json"}
    response = requests.post(url, data=json.dumps(data_request), headers=headers)
    text = json.loads(response.text)
    if text['status'] == 0:
        return text['data']
    else:
        return None


def detect(base64):
    """
    {'status': 0, 'message': '成功检测到人脸', 'data': [{'glasses': 0, 'height': 332, 'landmark': {'x': [69, 139, 108, 78, 137],
     'y': [144, 140, 181, 226, 224]}, 'left': 190, 'quality': 1, 'score': 0.9997692704200745, 'sideFace': 0, 'top': 66, 'width': 208}]}
    :param base64:
    :return:
    """
    data_request = {'image_base64': base64}
    url = 'http://192.168.1.11:2313/faces/detect'
    headers = {'content-type': "application/json"}
    response = requests.post(url, data=json.dumps(data_request), headers=headers)
    text = json.loads(response.text)
    #print(text)
    if text['status'] == 0:
        face = Face()
        data = text['data'][0]
        face.x = data['left']
        face.y = data['top']
        face.width = data['width']
        face.height = data['height']
        face.sideFace = data['sideFace']
        face.quality = data['quality']
        face.score = data['score']
        return face
    else:
        return None


def extract2(file_path):
    f = open(file_path, 'rb')
    b64 = base64.b64encode(f.read())
    return extract(b64)


def cosine(x, y):
    """
    求两个float数组的余弦
    :param x: 正则化的特征向量
    :param y: 正则化的特征向量
    :return:
    """
    #print("x norm: " , np.linalg.norm(x))
    #print("y norm: ", np.linalg.norm(y))
    #return np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y))
    return np.dot(x, y)

def zmq_detect(base64):
    '''
    zmq 版本的人脸检测：
    {"detect":[{"glasses":0.0,"height":332,
    "landmark":{"x":[69,139,108,78,137],"y":[144,140,181,226,224]},
    "left":190,"quality":1.0,"score":0.99976927042007446,"sideFace":0.0,"top":66,"width":208}],"detect_nums":1,
    "error_message":"601","request_id":"0422f291-2476-4997-8732-d25f8b8293b8","time_used":21,"track_nums":0}
    :param base64:
    :return:
    '''
    url = 'tcp://192.168.1.11:5559'
    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.connect(url)
    # print('connect ok!')
    data = {'interface': '5', 'api_key': '', 'image_base64': base64}
    data = json.dumps(data)
    socket.send_string(data)
    message = socket.recv()
    r = message[:-2]
    print('zmq detect received message: ', r)
    return r

def zmq_extract(base64, landmark):
    '''
    zmq 版本的人脸特征提取
    :param base64: crop 出来的人脸图像
    :param landmarks: detect 出来的landmark
    :return: 人脸特征
    '''
    url = 'tcp://192.168.1.11:5559'
    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.connect(url)
    data = {'interface': '6', 'api_key': '', 'faces': [{'image_base64': base64, 'landmark': landmark}]}
    data = json.dumps(data)
    print(data)
    socket.send_string(data)
    message = socket.recv()
    r = message[:-2]
    print('zmq extract feature: ', r)
    return r

if __name__ == '__main__':

    img = open('F:\\01.jpg', 'rb')
    b64 = base64.b64encode(img.read()).decode('utf-8')

    feature = extract(b64)
    zmq_d_result = json.loads(zmq_detect(b64))
    landmark = zmq_d_result['detect'][0]['landmark']
    f = detect(b64)
    # crop
    img = cv2.imread('F:\\01.jpg')
    crop_img = img[f.y:f.y + f.height, f.x:f.x + f.width]
    crop_img = cv2.imencode('.jpg', crop_img)[1]
    crop_b64 = str(base64.b64encode(crop_img))[2:-1]
    zmq_extract(crop_b64, landmark)
    # todo : zmq_extract return 10005 error, it need to be handle
    #cv2.imshow('t', crop_img)
    while True:
        if cv2.waitKey(5) == 27:
            break
    print()
