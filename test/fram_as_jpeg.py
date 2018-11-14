#!/usr/bin/env python
from __future__ import unicode_literals
import argparse
import ffmpeg
import sys, pdb
import numpy as np
import cv2

parser = argparse.ArgumentParser(
    description='Read individual video frame into memory as jpeg and write to stdout')
parser.add_argument('in_filename', help='Input filename')
parser.add_argument('frame_num', help='Frame number')


def read_frame_as_jpeg(in_filename, frame_num):
    out, err = (
        ffmpeg
            .input(in_filename)
            .output('pipe:', vframes=1, format='image2', vcodec='mjpeg')
            .run(capture_stdout=True)
    )
    return out

def video_info(input_file):
    probe = ffmpeg.probe(input_file)
    video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    width = int(video_info['width'])
    height = int(video_info['height'])
    #num_frames = int(video_info['nb_frames'])
    return width, height

def video_numpy(input_file, height, width):
    '''
    将视频文件全部读取到numpy数组中, 按照bgr顺序
    :return:
    '''
    out, _ = (
        ffmpeg
            .input(input_file)
            .output('pipe:', format='rawvideo', pix_fmt='bgr24')
            .run(capture_stdout=True)
    )
    video = np.frombuffer(out, np.uint8).reshape([-1, height, width, 3])
    return video


if __name__ == '__main__':
    #url = '../iec.mp4'
    url = 'rtsp://admin:iec123456@192.168.1.72:554/unicast/c1/s0/live'
    width, height = video_info(url)
    #video = video_numpy(url, height, width)

    out = read_frame_as_jpeg(url, 0)
    pdb.set_trace()
    img = np.frombuffer(out, np.uint8).reshape([height, width, 3])

    #cv2.imwrite('./hh.jpg', img)

    cv2.imwrite('./out.jpg', img)