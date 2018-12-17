import os
import sys

import cv2
import numpy as np

# get current file dir
sup = os.path.dirname(os.path.realpath(__file__))
sup = os.path.dirname(sup)
if sup not in sys.path:
    sys.path.append(sup)

from util import WeedClient

weed = WeedClient('192.168.1.6', 9333)

img = cv2.imread('F:\\man.jpg')
ret = weed.assign()
fid = ret['fid']
url = ret['url']
print(ret)
bs = cv2.imencode('.jpg', img)
ret = weed.upload(url, fid, bs[1], 'man.jpg')
print(ret)
img2 = weed.download('http://' + url + '/' + fid)
cv2.imshow('img', cv2.imdecode(np.fromstring(img2, np.uint8), cv2.IMREAD_COLOR))
cv2.waitKey(0)
