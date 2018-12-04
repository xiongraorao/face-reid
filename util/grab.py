from ctypes import cdll
from config import grab_lib

ffmpegPython = cdll.LoadLibrary(grab_lib)

class Grab():
    def __init__(self, url, rate, quality):
        pass

    def grab_image(self):
        pass

    def close(self):
        pass
