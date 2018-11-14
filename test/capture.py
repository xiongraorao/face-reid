from multiprocessing import Process, Queue, Pipe
import cv2, time
from config import camera


def grab(q, url):
    '''
    抓图
    :param q:
    :return:
    '''
    capture = cv2.VideoCapture(url)
    count = 0
    frame_rate = 2  # 每秒抓一帧
    while True:
        ret, img = capture.read()
        count += 1
        if int(count * frame_rate) % 25 != 0:
            continue
        if ret is False:
            count -= 1
            continue
        q.put(img)
        print('grab %d image' % count)
        count = 0


def show(q):
    while True:
        time.sleep(0.3)
        img = q.get()
        cv2.imshow('img', img)
        cv2.waitKey(0)
        print('size: ', q.qsize())


if __name__ == '__main__':
    q = Queue()
    url = camera['cross']
    p = Process(target=grab, args=(q, url))
    s = Process(target=show, args=(q,))
    p.start()
    s.start()
