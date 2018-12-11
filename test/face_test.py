import base64
import json

import cv2
import requests

from util.face import base64_to_bytes, Face

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
    # print(text)
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


def test():
    img = open('F:\\02.jpg', 'rb')
    b64 = base64.b64encode(img.read()).decode('utf-8')
    bys = base64_to_bytes(b64)
    f = open('F:\\sss.jpg', 'wb')
    f.write(bys)
    f.close()


if __name__ == '__main__':

    face = Face('tcp://192.168.1.11:5559')
    capture = cv2.VideoCapture(0)
    count = 0
    f = open('./result.txt', 'w')
    while True:
        ret, img = capture.read()
        count += 1
        if ret:
            image = cv2.imencode('.jpg', img)[1]
            b64 = str(base64.b64encode(image))[2:-1]
            result = face.detect(b64, field='track', image_id=str(count), camera_id='1')
            # result = face.detect(b64)
            for num in range(result['detect_nums']):
                print(num, ':', result['detect'][num])
                left = result['detect'][num]['left']
                top = result['detect'][num]['top']
                height = result['detect'][num]['height']
                width = result['detect'][num]['width']
                crop = face.crop(left, top, width, height, img)
                # cv2.imwrite('F:\\camera\\tt\\%s.jpg' % (str(count) + str(num)), crop)
                cv2.imshow('img', crop)
                # cv2.waitKey(1000)
                if 0xFF & cv2.waitKey(5) == 27:
                    break

    img = open('F:\\02.jpg', 'rb')
    b64 = base64.b64encode(img.read()).decode('utf-8')
    data = {'interface': '5', 'api_key': '', 'image_base64': b64}
    ret = face.detect(data)
    print(ret)

    img = open('F:\\02.jpg', 'rb')
    b64 = base64.b64encode(img.read()).decode('utf-8')

    # test for face_feature
    ret = face_feature(b64)
    print("len: ", len(ret['detect_info']), len(ret['feature']))
    # feature = extract(b64)
    zmq_d_result = json.loads(zmq_detect(b64))
    landmarks = zmq_d_result['detect'][0]['landmark']
    f = detect(b64)
    h_f = np.array(extract(b64))
    # crop
    img = cv2.imread('F:\\01.jpg')
    crop_img = img[f.y:f.y + f.height, f.x:f.x + f.width]
    crop_b64 = mat_to_base64(crop_img)
    z_f = zmq_extract(crop_b64, landmarks)
    z_f = json.loads(z_f)['feature'][0]
    z_f = np.array(z_f)
    print('sim: ', h_f.dot(z_f))
    cv2.imshow('t', crop_img)
    while True:
        if cv2.waitKey(5) == 27:
            break
    print()
