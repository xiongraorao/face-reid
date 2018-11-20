import json
import os
import sys
import time

import cv2
import numpy as np
import torch
from torch.autograd import Variable
from torchvision.transforms import transforms

ssd_path = os.path.abspath(os.path.join('..'))
if ssd_path not in sys.path:
    sys.path.append(ssd_path)
from  reid.model import ft_net
from PIL import Image
import torch.nn as nn
from ssd.data import VOC_CLASSES as lables
from ssd.ssd import build_ssd


def init(ssd_model_path, reid_model_path, device_id=0):
    '''
    初始化网络
    :return:
    '''
    print('start initialize ssd network ...')
    if torch.cuda.is_available():
        torch.set_default_tensor_type('torch.cuda.FloatTensor')
        torch.cuda.set_device(device_id)
    else:
        torch.set_default_tensor_type('torch.FloatTensor')
    net = build_ssd('test', 300, 21)
    net.load_weights(ssd_model_path)
    print(net)

    print('start initialize reid netword ...')
    model_structure = ft_net(751)
    model = load_network(model_structure, reid_model_path)
    model.model.fc = nn.Sequential()
    model.classifier = nn.Sequential()
    model = model.eval()
    if torch.cuda.is_available():
        model = model.cuda()
    print(model)
    return net, model


def detect(net, img_array, threshold=0.6):
    '''
    检测行人坐标，返回置信度
    :param threshold: 行人置信分数
    :arg img_array: bgr 顺序的图像数组
    :return:
    '''
    img_array = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
    x = cv2.resize(img_array, (300, 300)).astype(np.float32)
    x -= (104.0, 117.0, 123.0)
    x = x.astype(np.float32)
    x = x[:, :, ::-1].copy()
    x = torch.from_numpy(x).permute(2, 0, 1)
    xx = Variable(x.unsqueeze(0))
    if torch.cuda.is_available():
        xx = xx.cuda()
    y = net(xx)
    detections = y.data
    scale = torch.Tensor(img_array.shape[1::-1]).repeat(2)  # height, width, height, width
    result = []
    for i in range(detections.size(1)):
        j = 0
        while detections[0, i, j, 0] >= threshold:
            score = detections[0, i, j, 0]
            label_name = lables[i - 1]
            pt = (detections[0, i, j, 1:] * scale).cpu().numpy()
            ret = {}
            ret['score'] = float('%.3f' % (score.cpu().numpy().reshape(1)[0]))
            ret['x'] = int(pt[0])
            ret['y'] = int(pt[1])
            ret['w'] = int(pt[2] - pt[0] + 1)
            ret['h'] = int(pt[3] - pt[1] + 1)
            ret['label'] = label_name
            # 过滤掉非行人
            if label_name == 'person':
                result.append(json.dumps(ret))
            j += 1
    return result


def visual(img, landmark, scale=1.0):
    '''
    将检测的结果显示在图片上面
    :param img:
    :param landmark: detect的结果
    :return:
    '''
    h, w = img.shape[:2]
    img = cv2.resize(img, (int(scale * w), int(scale * h)), interpolation=cv2.INTER_CUBIC)
    for lm in landmark:
        lm = json.loads(lm)
        print('height: {}, width: {}'.format(h, w))
        cv2.rectangle(img, (int(lm['x'] * scale), int(lm['y'] * scale)),
                      (int((lm['x'] + lm['w']) * scale), int((lm['y'] + lm['h']) * scale)), (0, 255, 0), 2)
        cv2.putText(img, '%s : %f' % (lm['label'], lm['score']),
                    (int(lm['x'] * scale), int((lm['y'] + 10) * scale) if lm['y'] > 0 else 0), cv2.FONT_HERSHEY_SIMPLEX,
                    1 * scale, (0, 0, 255))
    return img


def load_network(network, model_path):
    network.load_state_dict(torch.load(model_path))
    return network


def fliplr(img):
    '''flip horizontal, 翻转图像的最后一维，W， 水平翻转'''
    inv_idx = torch.arange(img.size(3) - 1, -1, -1).long()  # N x C x H x W
    img_flip = img.index_select(3, inv_idx)
    return img_flip


def convert_img(img):
    '''
    转换图片
    :param img: PIL image  eg: Image.open('file.jpg')
    :return: tensor: 1*c*h*w -- normalized
    '''
    img = transforms.Resize((288, 144), interpolation=3)(img)
    img = transforms.ToTensor()(img)
    img = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])(img)
    img.unsqueeze_(0)
    return img


def extract_feature(model, img):
    '''
    img: IPL read
    :param model: 网络
    :param img: numpy
    :return: 1*2048 feature
    '''
    img = convert_img(img)
    ff = torch.FloatTensor(1, 2048).zero_()
    for i in range(2):
        if i == 1:
            img = fliplr(img)
        input_img = Variable(img.cuda())
        outputs = model(input_img)
        f = outputs.data.cpu()
        ff = ff + f
    fnorm = torch.norm(ff, p=2, dim=1, keepdim=True)
    ff = ff.div(fnorm.expand_as(ff))
    return ff


def crop(img, ped_pos, rectified = True, face_pos=None):
    '''
    裁剪检测出来的行人
    :param rectified: 是否启动行人过滤，false会排除检测到的不完整的行人
    :param img: 原始图像
    :param ped_pos: 行人坐标
    :param face_pos: 人脸坐标（起到过滤作用）dict
    :return: cropped pedestrian
    '''
    rets = []
    height, width = img.shape[:-1]
    for ped in ped_pos:
        ped = json.loads(ped)
        x = ped['x']
        y = ped['y']
        h = ped['h']
        w = ped['w']
        # 坐标修正
        is_inner = True # 行人是否在画面里面
        if rectified:
            x = 0 if x < 0 else x
            y = 0 if y < 0 else y
            h = height - y - 1 if y + h > height else  h
            w = width - x - 1 if x + w > width else w
        else:
            is_inner = x >=0 and x + w < width and y >=0 and y + h < height
        print('x: {}, y: {}, height: {}, width: {}'.format(x, y, h, w))
        if face_pos is not None:
            if face_pos['x'] >= x and face_pos['y'] >= y and face_pos['h'] <= h and face_pos['w'] <= w:
                rets.append(img[y:y + h, x:x + w]) # just add pedestrians which has include face_pos
                return rets
        elif is_inner:
            rets.append(img[y:y + h, x:x + w])
    return rets

if __name__ == '__main__':
    print('start detect pedestrian ...')
    image = cv2.imread('../bike.jpg', cv2.IMREAD_COLOR)
    net, reid_model = init('../model/ssd300_mAP_77.43_v2.pth', '../model/ft_ResNet50/net_last.pth')
    # capture = cv2.VideoCapture('rtsp://admin:123456@192.168.1.61:554/h264/ch1/main/av_stream') # ys
    # capture = cv2.VideoCapture('rtsp://admin:iec123456@192.168.1.71:554/unicast/c1/s0/live')  # hk
    # capture = cv2.VideoCapture('../secretstar.mkv')
    capture = cv2.VideoCapture('../iec.mp4')
    frame_rate = 0.5  # 每秒抓一帧
    count = 0
    cv2.namedWindow('result', cv2.WINDOW_AUTOSIZE)

    while True:
        if int(count * frame_rate) % 25 == 0:
            ret, img = capture.read()
            count = 0
        else:
            count += 1
            continue
        if img is None:
            continue
        # image = cv2.imencode('.jpg', img)[1]
        # image = cv2.imread(img, cv2.IMREAD_COLOR)
        start = time.time()
        h, w = img.shape[:2]
        # img = cv2.resize(img, (int(w/2), int(h/2)))
        result = detect(net, img)
        image = visual(img, result, 1)
        cv2.imshow('result', image)

        # extract pedestrian feature
        print('crop image from pedestrian')
        images = crop(img, result)

        if len(images) > 0:
            cv2.imshow('cropped image: ', images[0])
            ped_img = Image.fromarray(cv2.cvtColor(images[0], cv2.COLOR_BGR2RGB))
            ped_feature = extract_feature(reid_model, ped_img)
            print('ped_feature: ', ped_feature.cpu().numpy().tolist())
            print(result, ', time = ', time.time() - start)
        if 0xFF & cv2.waitKey(5) == 27:
            break
