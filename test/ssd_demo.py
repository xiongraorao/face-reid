import json
import cv2
import numpy as np
import torch
from torch.autograd import Variable
import time

import os,sys
ssd_path = os.path.abspath(os.path.join('..'))
if ssd_path not in sys.path:
    sys.path.append(ssd_path)
from util.face import get_list_files

from ssd.data import VOC_CLASSES as lables
from ssd.ssd import build_ssd


def init(model_path, device_id=0):
    '''
    初始化网络
    :return:
    '''
    print('start initialize network ...')
    if torch.cuda.is_available():
        torch.set_default_tensor_type('torch.cuda.FloatTensor')
        torch.cuda.set_device(device_id)
    else:
        torch.set_default_tensor_type('torch.FloatTensor')
    net = build_ssd('test', 300, 21)
    net.load_weights(model_path)
    print(net)
    return net

def detect(net, img_array, threshold=0.6):
    '''
    检测行人坐标，返回置信度
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
    scale = torch.Tensor(img_array.shape[1::-1]).repeat(2) # height, width, height, width
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
            result.append(json.dumps(ret))
            j+=1
    return result

def visual(img, landmark, scale=1.0):
    '''
    将检测的结果显示在图片上面
    :param img:
    :param landmark:
    :return:
    '''
    h, w = img.shape[:2]
    img = cv2.resize(img, (int(scale * w), int(scale * h)), interpolation=cv2.INTER_CUBIC)
    for lm in landmark:
        lm = json.loads(lm)
        print('height: {}, width: {}'.format(h,w))
        cv2.rectangle(img,(int(lm['x']*scale), int(lm['y']*scale)), (int((lm['x'] + lm['w'])*scale), int((lm['y'] + lm['h'])*scale)), (0,255,0 ), 2)
        cv2.putText(img,'%s : %f' % (lm['label'], lm['score']),(int(lm['x']*scale), int((lm['y'] + 10)*scale) if lm['y'] > 0 else 0),cv2.FONT_HERSHEY_SIMPLEX, 1*scale, (0,0,255))
    return img

if __name__ == '__main__':
    print('start detect pedestrian ...')
    image = cv2.imread('../bike.jpg', cv2.IMREAD_COLOR)
    net = init('../model/ssd300_mAP_77.43_v2.pth')
    data_dir = 'F:\\datasets\\lfw'
    img_list = get_list_files(data_dir)
    #capture = cv2.VideoCapture('rtsp://admin:123456@192.168.1.61:554/h264/ch1/main/av_stream') # ys
    capture = cv2.VideoCapture('rtsp://admin:iec123456@192.168.1.72:554/unicast/c1/s0/live') # hk
    #capture = cv2.VideoCapture('../secretstar.mkv')
    frame_rate = 0.5  # 每秒抓一帧
    count = 0
    #for img in img_list:
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
        #image = cv2.imencode('.jpg', img)[1]
        #image = cv2.imread(img, cv2.IMREAD_COLOR)
        start = time.time()
        h,w = img.shape[:2]
        #img = cv2.resize(img, (int(w/2), int(h/2)))
        result = detect(net, img)
        image = visual(img, result, 0.5)
        cv2.imshow('result', image)
        print(result , ', time = ', time.time() - start)
        if 0xFF & cv2.waitKey(5) == 27:
            break
