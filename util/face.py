#!/usr/bin/env python
# coding=utf-8

import base64
import json
import os
import requests
import cv2
import numpy as np


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
    print(text)
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
    :param x:
    :param y:
    :return:
    """
    return np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y))


if __name__ == '__main__':

    img = open('F:\\01.jpg', 'rb')
    b64 = base64.b64encode(img.read()).decode('utf-8')

    feature = extract(b64)
    print(cosine(feature,feature))

    f = detect(b64)
    # crop
    img = cv2.imread('F:\\01.jpg')
    crop_img = img[f.y:f.y + f.height, f.x:f.x + f.width]
    cv2.imshow('t', crop_img)
    while True:
        if cv2.waitKey(5) == 27:
            break
    print()
