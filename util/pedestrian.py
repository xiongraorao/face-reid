import json
import os
import sys

import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.autograd import Variable
from torchvision.transforms import transforms

# get current file dir
sup = os.path.dirname(os.path.realpath(__file__))
sup = os.path.dirname(sup)
if sup not in sys.path:
    sys.path.append(sup)

from reid.model import ft_net, ft_net_dense, PCB, PCB_test
from ssd.data import VOC_CLASSES as lables
from ssd.ssd import build_ssd


class Ped:
    '''
    行人检测和特征提取
    '''

    def __init__(self, args):
        self.opt = args
        self._init()

    def _init(self):
        '''
        网络初始化
        :param opt:
        :return:
        '''
        if torch.cuda.is_available():
            torch.set_default_tensor_type('torch.cuda.FloatTensor')  # fuck, this line let me debug a half day
            torch.cuda.set_device(self.opt.gpu_id)
        else:
            torch.set_default_tensor_type('torch.FloatTensor')

        if 'only_reid' not in self.opt or not self.opt.only_reid:
            print('start initialize ssd network ...')
            net = build_ssd('test', 300, 21)
            net.load_weights(self.opt.ssd_model)
            print(net)
            self.ssd_model = net

        print('start initialize reid network ...')
        if self.opt.use_dense:
            model_structure = ft_net_dense(751)
        else:
            model_structure = ft_net(751)
        if self.opt.PCB:
            model_structure = PCB(751)
        model = self.load_network(model_structure, self.opt.reid_model)

        if not self.opt.PCB:
            model.model.fc = nn.Sequential()
            model.classifier = nn.Sequential()
        else:
            model = PCB_test(model)
        model = model.eval()
        if torch.cuda.is_available():
            model = model.cuda()
        print(model)
        self.reid_model = model

    def detect(self, img_array, threshold=0.6):
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
        y = self.ssd_model(xx)
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

    def visual(self, img, landmark, scale=1.0):
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
                        (int(lm['x'] * scale), int((lm['y'] + 10) * scale) if lm['y'] > 0 else 0),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1 * scale, (0, 0, 255))
        return img

    def load_network(self, network, model_path):
        network.load_state_dict(torch.load(model_path))
        return network

    def fliplr(self, img):
        '''flip horizontal, 翻转图像的最后一维，W， 水平翻转'''
        inv_idx = torch.arange(img.size(3) - 1, -1, -1).long()  # N x C x H x W
        img_flip = img.index_select(3, inv_idx)
        return img_flip

    def convert_img(self, img):
        '''
        转换图片
        :param img: PIL image  eg: Image.open('file.jpg')
        :return: tensor: 1*c*h*w -- normalized
        '''
        if self.opt.PCB:
            img = transforms.Resize((384, 192), interpolation=3)(img)
        else:
            img = transforms.Resize((288, 144), interpolation=3)(img)
        img = transforms.ToTensor()(img)
        img = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])(img)
        img.unsqueeze_(0)
        return img

    def extract_feature(self, img):
        '''
        img: IPL read
        :param model: 网络
        :param img: numpy
        :return: 1*2048 feature
        '''
        img = self.convert_img(img)
        img = img.cuda()
        if self.opt.use_dense:
            ff = torch.FloatTensor(1, 1024).zero_()
        else:
            ff = torch.FloatTensor(1, 2048).zero_()
        if self.opt.PCB:
            ff = torch.FloatTensor(1, 2048, 6).zero_()
        for i in range(2):
            if i == 1:
                img = self.fliplr(img)
            input_img = Variable(img)
            outputs = self.reid_model(input_img)
            f = outputs.data.cpu()
            ff = ff + f
        if self.opt.PCB:
            fnorm = torch.norm(ff, p=2, dim=1, keepdim=True) * np.sqrt(6)
            ff = ff.div(fnorm.expand_as(ff))
            ff = ff.view(ff.size(0), -1)
        else:
            fnorm = torch.norm(ff, p=2, dim=1, keepdim=True)
            ff = ff.div(fnorm.expand_as(ff))
        return ff

    def crop(self, img, ped_pos, rectified=True, face_pos=None):
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
            is_inner = True  # 行人是否在画面里面
            if rectified:
                x = 0 if x < 0 else x
                y = 0 if y < 0 else y
                h = height - y - 1 if y + h > height else h
                w = width - x - 1 if x + w > width else w
            else:
                is_inner = x >= 0 and x + w < width and y >= 0 and y + h < height
            print('x: {}, y: {}, height: {}, width: {}'.format(x, y, h, w))
            if face_pos is not None:
                if face_pos['x'] >= x and face_pos['y'] >= y and face_pos['h'] <= h and face_pos['w'] <= w:
                    rets.append(img[y:y + h, x:x + w])  # just add pedestrians which has include face_pos
                    return rets
            elif is_inner:
                rets.append(img[y:y + h, x:x + w])
        return rets


def grab(q, url, frame_rate=1, logger=None):
    '''
    抓图
    :param frame_rate: 每秒抓几帧
    :param q:
    :return:
    '''
    # print('启动抓取线程，url: %s, frame_rate: %d' % (url, frame_rate))
    if logger is not None:
        logger.info('[grab] 启动抓取线程，url: %s, frame_rate: %d' % (url, frame_rate))
    capture = cv2.VideoCapture(url)
    count = 0
    count2 = 0
    try:
        while True:
            ret, img = capture.read()
            count += 1
            if int(count * frame_rate) % 25 != 0:
                continue
            if ret is False:
                count -= 1
                continue
            q.put(img)
            count = 0
            count2 += 1
            # print('[grab] grab %d image' % count2)
            if logger is not None:
                logger.info('[grab] grab %d image' % count2)
    except KeyboardInterrupt:
        print('key interrupted , grab process exit')
        exit()
