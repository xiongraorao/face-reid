import argparse
import os
import sys

reid_path = os.path.abspath(os.path.join('..'))
if reid_path not in sys.path:
    sys.path.append(reid_path)
import torch
from PIL import Image
from util.pedestrian import Ped

parser = argparse.ArgumentParser(description='compute the similarity of two pedestrian')
parser.add_argument('img1', type=str, help='img1')
parser.add_argument('img2', type=str, help='img2')
parser.add_argument('--reid_model', '-m', default='reid/model/dense121/net_49.pth', help='reid model path')
parser.add_argument('--gpu_id', type=int, default=0, help='gpu device number')
parser.add_argument('--use_dense', action='store_true', help='use densenet121')
parser.add_argument('--PCB', action='store_true', help='use PCB')
parser.add_argument('--only_reid', action='store_true', help='just do pedestrian re-id')

args = parser.parse_args()
ped = Ped(args)

img1 = Image.open(args.img1)
img2 = Image.open(args.img2)

f1 = ped.extract_feature(img1)
f2 = ped.extract_feature(img2)
sim = torch.mm(f1, f2.reshape(-1, 1))
print('sim = %f' % sim)