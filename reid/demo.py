import os,sys
reid_path = os.path.abspath(os.path.join('..'))
if reid_path not in sys.path:
    sys.path.append(reid_path)
import torch
from torch.autograd import Variable
from torchvision.transforms import transforms
from  reid.model import ft_net
from PIL import Image
import torch.nn as nn
import cv2
import pdb

def load_network(network, model_path):
    network.load_state_dict(torch.load(model_path))
    return network

def fliplr(img):
    '''flip horizontal, 翻转图像的最后一维，W， 水平翻转'''
    inv_idx = torch.arange(img.size(3)-1,-1,-1).long()  # N x C x H x W
    img_flip = img.index_select(3,inv_idx)
    return img_flip

def convert_img(img):
    '''
    转换图片
    :param img: PIL image  eg: Image.open('file.jpg')
    :return: tensor: 1*c*h*w -- normalized
    '''
    img = transforms.Resize((288,144), interpolation=3)(img)
    img = transforms.ToTensor()(img)
    img = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])(img)
    img.unsqueeze_(0)
    return img

def extract_feature(model, img):
    '''
    img: IPL read
    :param model: 网络
    :param img: IPL Image
    :return: 1*2048 feature
    '''
    img = convert_img(img)
    ff = torch.FloatTensor(1, 2048).zero_()
    for i in range(2):
        if (i == 1):
            img = fliplr(img)
        input_img = Variable(img.cuda())
        outputs = model(input_img)
        f = outputs.data.cpu()
        ff = ff + f
    fnorm = torch.norm(ff, p=2, dim=1, keepdim=True)
    ff = ff.div(fnorm.expand_as(ff))
    return ff

if __name__ == '__main__':
    model_structure = ft_net(751)
    model_path = '../model/ft_ResNet50/net_last.pth'
    model = load_network(model_structure, model_path)
    model.model.fc = nn.Sequential()
    model.classifier = nn.Sequential()
    model = model.eval()
    if torch.cuda.is_available():
        model = model.cuda()
    img = Image.open('../img/0567/0567_c1s3_021401_00.jpg')
    img2 = Image.open('../img/0567/0567_c2s2_003887_00.jpg')
    img3 = Image.open('../img/0568/0568_c3s2_005237_00.jpg')
    img4 = Image.open('../img/0568/0568_c5s2_005805_00.jpg')
    feature = extract_feature(model, img)
    feature2 = extract_feature(model, img2)
    feature3 = extract_feature(model, img3)
    feature4 = extract_feature(model, img4)

    #print(feature.cpu().numpy())
    #pdb.set_trace()

    d1 = torch.mm(feature, feature2.reshape(-1, 1))
    d2 = torch.mm(feature, feature3.reshape(-1, 1))
    d3 = torch.mm(feature2, feature3.reshape(-1,1))
    d4 = torch.mm(feature4, feature3.reshape(-1,1))
    d5 = torch.mm(feature2, feature4.reshape(-1,1))

    print('d1: same person sim = ', d1)
    print('d2: not same person sim = ', d2)
    print('d3: not same person sim = ', d3)
    print('d4: same person sim = ', d4)
    print('d5: not same person sim = ', d5)

