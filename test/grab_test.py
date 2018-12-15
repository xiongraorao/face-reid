import sys,os
import time

sup = os.path.dirname(os.path.realpath(__file__))
sup = os.path.dirname(sup)
if sup not in sys.path:
    sys.path.append(sup)

print(sys.path)
from util import Grab

def test(id):
    # grab = Grab('rtsp://admin:iec123456@192.168.1.72:554/unicast/c1/s0/live', 5)
    grab = Grab('rtsp://admin:iec123456@192.168.1.70:554/unicast/c1/s0/live', 5)
    print(grab)
    while True:
        img = grab.grab_image()
        if img is not None:
            print(img[0][0][0])
            time.sleep(1)
            print('process id = ', id, ', pid = ', os.getpid())
            print(grab)
test(4)
