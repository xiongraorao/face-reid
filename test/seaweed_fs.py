import os
import sys

import cv2
import numpy as np

# get current file dir
sup = os.path.dirname(os.path.realpath(__file__))
sup = os.path.dirname(sup)
if sup not in sys.path:
    sys.path.append(sup)

from util import WeedMaster, WeedVolume

weed = WeedMaster('192.168.1.6', 9333)
# weed.assign()
# weed.lookup("17,03eb52d0de")
# weed.status()

weed2 = WeedVolume('192.168.1.6', 38080)

img = cv2.imread('F:\\man.jpg')
ret = weed.assign()
fid = ret['fid']
print(ret)
bs = cv2.imencode('.jpg', img)
ret = weed2.upload(fid, bs[1], 'man.jpg')
print(ret)
img2 = weed2.dowload(fid)
cv2.imshow('img', cv2.imdecode(np.fromstring(img2, np.uint8), cv2.IMREAD_COLOR))
cv2.waitKey(0)
