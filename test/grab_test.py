import sys,os
import time

sup = os.path.dirname(os.path.realpath(__file__))
sup = os.path.dirname(sup)
if sup not in sys.path:
    sys.path.append(sup)

from util import Grab

def test(id):
    # grab = Grab('rtsp://admin:iec123456@192.168.1.72:554/unicast/c1/s0/live', 5)
    grab = Grab('rtsp://admin:iec123456@192.168.1.71:554/unicast/c1/s0/live', 25)
    print(grab)
    while True:
        t1 = time.time()
        img = grab.grab_image()
        if img is not None:
            print(img[0][0][0])
            print('process id = ', id, ', pid = ', os.getpid())
            print(grab)
        print('cost time: %d ms '%(round((time.time() - t1)*1000)))
test(4)
