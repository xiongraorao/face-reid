import os
from ctypes import *

import cv2
import numpy as np

from .error import CAM_INIT_ERR, CAM_GRAB_ERR
from .logger import Log


class Grab():
    def __init__(self, url, rate, use_gpu = False):
        '''
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
        :param url:
        :param rate:
        :param use_gpu:
        '''
        self.url = url
        self.rate = rate
        lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'linux-build-cmake-make',
                                'ffmpeg-python.so')
        self.ffmpegPython = cdll.LoadLibrary(lib_path)
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
            try:
                e = CAM_INIT_ERR[self.initErr]
                self.logger.warning('grab initialize failed, error_message: ' + e)
            except KeyError:
                self.logger.warning('grab initialize failed, unknown error')
            finally:
                self.close()

    def __str__(self):
        return 'Grab Object(url: %s, rate: %d, initErr: %d, width: %d, height: %d)' % (
        self.url, self.rate, self.initErr, self.width, self.height)

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
            self.__release(tmp_buf)
            return img
        else:
            try:
                e = CAM_GRAB_ERR[error.value]
                self.logger.warning('grab failed , error message: ' + e)
            except KeyError:
                self.logger.error('grab failed, unknown error!')
            finally:
                return None

    def __release(self, tmp_buf):
        self.ffmpegPython.freeImageBuffer(tmp_buf)

    def close(self):
        self.ffmpegPython.destroy()
