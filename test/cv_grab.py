import cv2
import time

capture = cv2.VideoCapture("rtsp://100.98.0.240:8000/42012401001222334432_1")

while True:
    start = time.time()
    ret, img = capture.read()
    if ret is not False:
        cv2.imshow('img', img)
        if 0xFF & cv2.waitKey(5) == 27:
            break
    end = time.time()
    print("lantency: %f ms " % ((end - start)*1000))
    print('shape: ', img.shape)
capture.release()
cv2.destroyAllWindows()