import base64
import json
import os
import requests
import cv2
import numpy as np
import zmq
#from .logger import Log

#logger = Log('face', 'logs/')

class Face:
    def __init__(self, url):
        '''
        人脸检测，特征提取类，多线程环境下必须使用多个实例调用
        :param url:
        '''
        context = zmq.Context()
        self.socket = context.socket(zmq.DEALER)
        self.socket.connect(url)
        #logger.info('face api initialized completed')

    def detect(self, image_base64, field = None, image_id = None, camera_id = None):
        '''
        检测人脸
        :param image_base64: 图片base64编码
        :param field:
        :param image_id:
        :param camera_id:
        :return:
        '''
        data = {'interface': '5', 'api_key': '', 'image_base64': image_base64}
        if field is not None:
            data['field'] = field
        if image_id is not None:
            data['image_id'] = image_id
        if camera_id is not None:
            data['camera_id'] = camera_id
        data = json.dumps(data)
        self.socket.send_string(data)
        message = self.socket.recv_string()[:-2]
        return json.loads(message)

    def extract(self, image_base64, landmarks):
        '''
        提取人脸特征
        :param image_base64: 图片的base64位编码
        :param landmarks: detect接口返回的人脸位置信息
        :return:
        '''
        data = {'interface': '6', 'api_key': '', 'image_base64': base64, 'landmarks': landmarks}

        data = json.dumps(data)
        self.socket.send_string(data)
        message = self.socket.recv_string()[:-2]
        return json.loads(message)

    def crop(self, left, top, width, height, origin_img):
        '''
        图片裁剪
        :param left:
        :param top:
        :param width:
        :param height:
        :param origin_img: 原图
        :return:
        '''
        # 坐标修正
        origin_h, origin_w = origin_img.shape[:-1]
        left = 0 if left < 0 else left
        top = 0 if top < 0 else top
        width = origin_w - left - 1 if left + width > origin_w else width
        height = origin_h - top - 1 if top + height > origin_h else height
        crop_img = origin_img[top:top+height, left:left+width]
        return crop_img

    def close(self):
        self.socket.close()


def get_list_files(path):
    ret = []
    for root, dirs, files in os.walk(path):
        for filespath in files:
            ret.append(os.path.join(root, filespath))
    return ret


# def extract(base64):
#     '''
#     提取人脸
#     {'status': 0, 'message': '成功获取到人脸特征', 'data': [0.02387029491364956, ..., 0.053947705775499344]}
#     :param base64:
#     :return:
#     '''
#     data_request = {'image_base64': base64}
#     url = 'http://192.168.1.11:2313/faces/feature'
#     headers = {'content-type': "application/json"}
#     response = requests.post(url, data=json.dumps(data_request), headers=headers)
#     text = json.loads(response.text)
#     if text['status'] == 0:
#         return text['data']
#     else:
#         return None
#
#
# def detect(base64):
#     """
#     {'status': 0, 'message': '成功检测到人脸', 'data': [{'glasses': 0, 'height': 332, 'landmark': {'x': [69, 139, 108, 78, 137],
#      'y': [144, 140, 181, 226, 224]}, 'left': 190, 'quality': 1, 'score': 0.9997692704200745, 'sideFace': 0, 'top': 66, 'width': 208}]}
#     :param base64:
#     :return:
#     """
#     data_request = {'image_base64': base64}
#     url = 'http://192.168.1.11:2313/faces/detect'
#     headers = {'content-type': "application/json"}
#     response = requests.post(url, data=json.dumps(data_request), headers=headers)
#     text = json.loads(response.text)
#     #print(text)
#     if text['status'] == 0:
#         face = Face()
#         data = text['data'][0]
#         face.x = data['left']
#         face.y = data['top']
#         face.width = data['width']
#         face.height = data['height']
#         face.sideFace = data['sideFace']
#         face.quality = data['quality']
#         face.score = data['score']
#         return face
#     else:
#         return None
#
#
# def extract2(file_path):
#     f = open(file_path, 'rb')
#     b64 = base64.b64encode(f.read())
#     return extract(b64)


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
    r = message[:-2].decode('utf-8')
    # print('zmq detect received message: ', r)
    return r

def zmq_extract(base64, landmarks):
    '''
    zmq 版本的人脸特征提取
    {"dimension":256,"error_message":"701","feature":[[0.026357347145676613 ,..., 0.061496846377849579]],"request_id":"76b43a14-d9c3-4be3-8b2a-a204f439f506","time_used":16}
    :param base64: crop 出来的人脸图像的base64 数组
    :param landmarks: detect 出来的landmark 数组
    :return: 人脸特征
    '''
    url = 'tcp://192.168.1.11:5559'
    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.connect(url)
    data = {'interface': '6', 'api_key': '', 'image_base64': base64, 'landmarks': landmarks}
    data = json.dumps(data)
    #socket.send_string(data)
    socket.send_json(data)
    message = socket.recv()
    r = message[:-2].decode('utf-8')
    # print('zmq extract feature: ', r)
    return r

def mat_to_base64(img_np):
    '''
    opencv 的数组转base64
    :param img_np:
    :return:
    '''
    image = cv2.imencode('.jpg', img_np)[1]
    base64_data = str(base64.b64encode(image))[2:-1]
    return base64_data

def base64_to_mat(b64):
    '''
    base64 转opencv 数组
    :param b64:
    :return:
    '''
    nparr = np.fromstring(base64.b64decode(b64), np.uint8)
    img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img_np

def face_feature(base64):
    '''
    获取当前图片中所有的人脸信息以及对应的特征
    '''
    ret = {}
    detect_result = json.loads(zmq_detect(base64))
    # crop
    origin_img = base64_to_mat(base64)
    landmarks = []
    b64s = []
    detect_infos = []
    features = [[]]
    for i in range(detect_result['detect_nums']):
        x = detect_result['detect'][i]['left']
        y = detect_result['detect'][i]['top']
        w = detect_result['detect'][i]['width']
        h = detect_result['detect'][i]['height']
        sideFace = detect_result['detect'][i]['sideFace']
        quality = detect_result['detect'][i]['quality']
        score = detect_result['detect'][i]['score']
        glasses = detect_result['detect'][i]['glasses']
        detect_info = {'x':x, 'y':y, 'w':w, 'h':h, 'sideFace':sideFace,
                       'quality':quality, 'score':score, 'glasses':glasses}
        landmark = detect_result['detect'][i]['landmark']
        b64 = mat_to_base64(origin_img[y:y+h, x:x+w])
        landmarks.append(landmark)
        b64s.append(b64)
        detect_infos.append(detect_info)
    # extract feature
    if detect_result['detect_nums'] > 0:
        extract_result = json.loads(zmq_extract(b64s, landmarks))
        features = extract_result['feature'] # 二维的list
    ret['detect_info'] = detect_infos
    ret['feature'] = features
    return ret

if __name__ == '__main__':

    face = Face('tcp://192.168.1.11:5559')
    capture = cv2.VideoCapture(0)
    count = 0
    f = open('./result.txt','w')
    while True:
        ret, img = capture.read()
        count += 1
        if ret:
            image = cv2.imencode('.jpg', img)[1]
            b64 = str(base64.b64encode(image))[2:-1]
            result = face.detect(b64,field='track', image_id=str(count), camera_id='1')
            # result = face.detect(b64)
            for num in range(result['detect_nums']):
                print(num, ':', result['detect'][num])
                left = result['detect'][num]['left']
                top = result['detect'][num]['top']
                height = result['detect'][num]['height']
                width = result['detect'][num]['width']
                crop = face.crop(left,top, width, height,img)
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
    #feature = extract(b64)
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
