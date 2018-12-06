from ctypes import *
import cv2
import numpy as np
from logger import Log
import time
import os
# initErr:
#       0:      success
#       -1      network init error
#       -2      couldn't open url
#       -3      has no video stream
#       -4      find video stream error
#       -5      find decoder error
#       -6      parse codec error
#       -7      malloc stream context error
#       -8      copy codec params error
#       -9      open codec error
#       -10     find video frame error

class Grab():
    def __init__(self, url, rate, use_gpu = False):
        self.url = url
        self.rate = rate
        self.ffmpegPython = cdll.LoadLibrary('../linux-build-cmake-make/ffmpeg-python.so')
        self.ffmpegPython.init.argtypes = [c_char_p, c_bool, c_bool, POINTER(c_int), POINTER(c_int)]
        self.ffmpegPython.init.restype = c_int
        self.logger = Log('grab', is_save=False)

        # init ffmpeg
        width = c_int()
        pwidth = pointer(width)
        height = c_int()
        pheight = pointer(height)
        self.width = 0
        self.height = 0
        self.initErr = self.ffmpegPython.init(url.encode("utf8"), True, use_gpu, pwidth, pheight)
        if self.initErr == 0:
            self.width = width.value
            self.height = height.value
            self.logger.info('grab initialize success!')
        else:
            error_msg = {
                -1: 'network init error',
                -2: 'could not open url',
                -3: 'has no video stream',
                -4: 'find video stream error',
                -5: 'find decoder error',
                -6: 'parse codec error',
                -7: 'malloc stream context error',
                -8: 'copy codec params error',
                -9: 'open codec error',
                -10: 'find video frame error'
            }
            try:
                e = error_msg[self.initErr]
                self.logger.warning('grab initialize failed, error_message: ' + e)
            except KeyError:
                self.logger.warning('grab initialize failed, unknown error')
            finally:
                self.close()
    def get_pid(self):
        return os.getpid()

    def start(self):
        '''
        开始抓图，并发送kafka消息队列中
        :return:
        '''
        pass

    def grab_image(self):
        '''
        抓图
        # error:
        #       0:              success
        #       -1              malloc frame error
        #       -2              malloc packet error
        #       -3              has no video stream
        #       -4              decode packet error
        #       -5              decode frame error
        #       -6              data is null, network may be error
        #       -10 or -20      malloc new frame error
        #       -30             not init error
        :return:
        '''
        self.ffmpegPython.getImageBuffer.argtypes = [c_int, c_int, c_int, POINTER(c_ulong), POINTER(c_int)]
        self.ffmpegPython.getImageBuffer.restype = c_void_p
        size = c_ulong()
        psize = pointer(size)
        error = c_int()
        perror = pointer(error)
        pbuffer = self.ffmpegPython.getImageBuffer(self.rate, 1, 100, psize, perror)
        if error.value == 0:
            UINIT8_TYPE = c_uint8 * size.value
            tmp_buf = cast(pbuffer, POINTER(UINIT8_TYPE))
            img = np.frombuffer(tmp_buf.contents, dtype=np.uint8)
            img = img.reshape(self.height, self.width , 3)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            self.logger.info('grab success, size = %d' % size.value)
            self.release(tmp_buf)
            return img
        else:
            error_msg = {
                -1: 'malloc frame error',
                -2: 'malloc packet error',
                -3: 'has no video stream',
                -4: 'decode packet error',
                -5: 'decode frame error',
                -6: 'data is null, network may be error',
                -10: 'malloc new frame error',
                -20: 'malloc new frame error',
                -30: 'not init error'
            }
            try:
                e = error_msg[error.value]
                self.logger.warning('grab failed , error message: ' + e)
            except KeyError:
                self.logger.error('grab failed, unknown error!')
            finally:
                return None

    def release(self, tmp_buf):
        self.ffmpegPython.freeImageBuffer(tmp_buf)

    def close(self):
        self.ffmpegPython.destroy()

def test(id):
    grab = Grab('rtsp://admin:iec123456@192.168.1.72:554/unicast/c1/s0/live', 5, 1)
    while True:
        img = grab.grab_image()
        if img is not None:
            print(img[0][0][0])
            time.sleep(1)
            print('process id = ', id, ', pid = ', os.getpid())

if __name__ == '__main__':
    grab = Grab('rtsp://admin:iec123456@192.168.1.72:554/unicast/c1/s0/live', 1)
    for i in range(100):
        img = grab.grab_image()
        if img is not None:
            cv2.imwrite('img/%d.jpg' % i, img)
            print(img[100], 'count = ', i)
    # import multiprocessing as mp
    # pool = mp.Pool(4)
    # for i in range(4):
    #     pool.apply_async(test,args=(i,))
    # #pool.join()
    # time.sleep(1000)
    # print('over')
