import util.pedestrian as Ped
import argparse
import os,sys
reid_path = os.path.abspath(os.path.join('..'))
if reid_path not in sys.path:
    sys.path.append(reid_path)
from  reid.model import ft_net
import torch
from torch.autograd import Variable
from torchvision.transforms import transforms
from  reid.model import ft_net
from PIL import Image
import torch.nn as nn
from util.pedestrian import load_network, extract_feature
import numpy as np

parser = argparse.ArgumentParser(description='compute the similarity of two pedestrian')
parser.add_argument('img1', type=str, help='img1')
parser.add_argument('img2', type=str, help='img2')
args = parser.parse_args()

model_structure = ft_net(751)
model_path = 'model/ft_ResNet50/net_last.pth'
model = load_network(model_structure, model_path)
model.model.fc = nn.Sequential()
model.classifier = nn.Sequential()
model = model.eval()
if torch.cuda.is_available():
    model = model.cuda()
img1 = Image.open(args.img1)
img2 = Image.open(args.img2)

f1 = extract_feature(model, img1)
f2 = extract_feature(model, img2)
sim = torch.mm(f1, f2.reshape(-1, 1))
print('sim = %f' % sim)