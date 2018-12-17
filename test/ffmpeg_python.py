from ctypes import *

import pdb
import time
import os

ffmpegPython = cdll.LoadLibrary('./linux-build-cmake-make/ffmpeg-python.so')

rtspUrl = "rtsp://admin:iec123456@192.168.1.72:554/unicast/c1/s0/live"

width = c_int()
pwidth = pointer(width)
height = c_int()
pheight = pointer(height)

# char *input_filename, bool nobuffer, bool use_gpu, int timeout, [out] width, [out] height
ffmpegPython.init.argtypes = [c_char_p, c_bool, c_bool, c_int, POINTER(c_int), POINTER(c_int)]
ffmpegPython.init.restype = c_int
initErr = ffmpegPython.init(rtspUrl.encode("utf8"), False, False, 2, pwidth, pheight)

print(width.value)
print(height.value)

print(initErr)
print(os.getpid())
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

if (initErr == 0):
        for i in range(2000):
                # int chose_frames, int type (YUV = 0, RGB = 1, JPEG = 2), int quality (JPEG; 1~100)
                ffmpegPython.getImageBuffer.argtypes = [c_int, c_int, c_int, POINTER(c_ulong), POINTER(c_int)]
                ffmpegPython.getImageBuffer.restype = c_void_p
        size = c_ulong()
        psize = pointer(size)

        error = c_int()
        perror = pointer(error)

        # int chose_frames, int type (YUV = 0, RGB = 1, JPEG = 2), int quality (JPEG; 1~100)
        ffmpegPython.getImageBuffer.argtypes = [c_int, c_int, c_int, POINTER(c_ulong), POINTER(c_int)]
        ffmpegPython.getImageBuffer.restype = c_void_p

        while (True):
                i += 1

                time.sleep(1)
                pbuffer = ffmpegPython.getImageBuffer(5, 1, 80, psize, perror)

                print(error.value)
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

#                if (error.value == 0):
#                        UINIT8_TYPE = c_uint8 * size.value
#
#                        tmp_buf = cast(pbuffer, POINTER(UINIT8_TYPE))
#
#                        t = "./tmp/images/test" + str(i) + ".rgb"
#
#                        with open(t, 'wb') as target:
#                                target.write(tmp_buf.contents)
#                else:
#                        ffmpegPython.destroy()
#                        break
#
        ffmpegPython.destroy()
