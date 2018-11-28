import subprocess as sp
import numpy as np
import cv2

input_file = 'rtsp://admin:iec123456@192.168.1.72:554/unicast/c1/s0/live'
width = 3072
height = 2048
command_in = ['ffmpeg',
            '-i', input_file,
            #'-f', 'image2pipe',
            #'-c:v', 'mjpeg',
            '-f', 'rawvideo',
            '-rtsp_transport', 'tcp',
            '-fflags', 'nobuffer',
            '-pix_fmt', 'rgb24',
            '-']
# p = sp.Popen(['ffmpeg'], stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
# out, err = p.communicate(('-i rtsp'))

pipe_in = sp.Popen(command_in, stdout=sp.PIPE, bufsize=10**8)

count = 0

while True:
    raw_image = pipe_in.stdout.read(width*height*3)

    image = np.fromstring(raw_image, dtype=np.uint8)
    if (len(image) == 0):
        break
    image = image.reshape((height, width,3)).copy()
    print('grab image: ')
    #print(image)
    #cv2.imshow(image)
    cv2.imwrite('img/test-%d.jpg'%(count), image)
    count += 1
    #cv2.waitKey(0)