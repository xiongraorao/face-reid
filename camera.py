import cv2
import time

capture = cv2.VideoCapture("rtsp://admin:iec123456@192.168.1.71:554/unicast/c1/s0/live")

while True:
    start = time.time()
    ret, img = capture.read()
    if ret is not False:
        cv2.imshow('img', img)
        if 0xFF & cv2.waitKey(5) == 27:
            break
    end = time.time()
    print("lantency: %f ms " % ((end - start)*1000))
capture.release()
cv2.destroyAllWindows()