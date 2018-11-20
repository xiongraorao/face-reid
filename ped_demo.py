'''
行人检测的Demo
'''
import json
import os
import time
import uuid
from multiprocessing import Process, Queue
import queue
import threading

import cv2
import numpy as np
import redis
from PIL import Image

from cluster.measure import Sample
from config import *
from util import pedestrian as Ped
from util.face import face_feature, cosine, mat_to_base64

output_dir = '/home/xrr/output2'

def redis_connect():
    pool = redis.ConnectionPool(host=redis_host, port=redis_port, db=ped_db)
    r = redis.Redis(connection_pool=pool)
    return r

def get_all_samples():
    '''
    从redis数据库读取数据... 存储格式：key: 样本名，value: {'vector':[], 'c_name':'', 'ped_vector': '', ...}
    :return: samples 的list
    '''
    r = redis_connect()
    keys = r.keys('*')
    samples = []
    for key in keys:
        content = r.get(key)
        content = json.loads(content.decode('utf-8'))
        sample = Sample(key.decode('utf-8'), content['vector'], content['c_name'], content['ped_vector'])
        samples.append(sample)
    return samples


def grab(q, url, frame_rate = 1):
    '''
    抓图
    :param q:
    :return:
    '''
    capture = cv2.VideoCapture(url)
    count = 0
    #frame_rate = 2  # 每秒抓几帧
    try:
        while True:
            ret, img = capture.read()
            count += 1
            if int(count * frame_rate) % 25 != 0:
                continue
            if ret is False:
                count -= 1
                continue
            q.put(img)
            print('grab %d image' % (count * frame_rate/25))
            count += 1
    except KeyboardInterrupt:
        print('key interrupted , grab process exit')
        exit()

def process(q):
    '''
    处理进程
    :param q:
    :return:
    '''
    r = redis_connect()
    # first load from redis
    samples = get_all_samples()
    up_th = 0.75  # 上阈值
    down_th = 0.6  # 下阈值
    ped_th = 0.93
    person_threshold = 0.85
    resize_scale = 0.5
    top_k = 10
    count = 0

    # initial ssd and reid
    ssd_model, reid_model = Ped.init('model/ssd300_mAP_77.43_v2.pth', 'model/ft_ResNet50/net_last.pth', gpu_id)

    print('start process images')
    try:
        while True:
            img = q.get()
            start = time.time()
            img = cv2.resize(img, None, fx=resize_scale, fy=resize_scale, interpolation=cv2.INTER_CUBIC)
            height, width = img.shape[:-1]
            b = mat_to_base64(img)
            #faces = face_feature(b)
            #face_num = len(faces['detect_info'])
            ped_result = Ped.detect(ssd_model, img, person_threshold)
            ped_imgs = Ped.crop(img, ped_result, False)

            for i,ped_img in enumerate(ped_imgs):
                ped_img_PIL = Image.fromarray(cv2.cvtColor(ped_img, cv2.COLOR_BGR2RGB))
                ped_feature = Ped.extract_feature(reid_model, ped_img_PIL).cpu().numpy().tolist()[0]
                feature = [] # 不考虑人脸特征，人脸特征为空

                # 和redis库里面所有的样本进行比对
                max_sim = -1.0
                max_sim_cname = 'MAX_CNAME'
                max_sim_ped_vector = []

                if len(samples) > 0:
                    vectors = np.array([x.ped_vector for x in samples])
                    sims = np.dot(vectors, np.array(ped_feature).T).reshape(-1, )
                    sims_top = np.argsort(-sims)[:top_k]
                    max_sim = sims[sims_top[0]]
                    max_sim_cname = samples[sims_top[0]].c_name
                    max_sim_ped_vector = samples[sims_top[0]].ped_vector

                # 为新生成的ID做准备
                c_name = str(uuid.uuid4())
                s_name = str(uuid.uuid4())

                if max_sim < ped_th:
                    # 新建一个新的行人ID
                    print('不是同一个行人，新建ID')
                    content = {'vector': feature, 'c_name': c_name, 'ped_vector': ped_feature}
                    r.set(s_name, json.dumps(content))
                    samples.append(Sample(s_name, feature, c_name, ped_feature))
                    dire = output_dir + os.sep + c_name
                    if not os.path.exists(dire):
                        os.mkdir(dire)
                    cv2.imwrite(dire + os.sep + s_name + '.jpg', ped_img)

                else:
                    print('同一个行人，合并')
                    content = {'vector': feature, 'c_name': max_sim_cname, 'ped_vector': ped_feature}
                    r.set(s_name, json.dumps(content))
                    samples.append(Sample(s_name, feature, max_sim_cname, ped_feature))
                    dire = output_dir + os.sep + max_sim_cname
                    if not os.path.exists(dire):
                        os.mkdir(dire)
                    cv2.imwrite(dire + os.sep + s_name + '.jpg', ped_img)
                #cv2.putText(ped_img, 'max_sim: %f'% (max_sim), (100,100), cv2.FONT_HERSHEY_SIMPLEX, 6, (0,0,255), 2)
                img = Ped.visual(img, ped_result)
                cv2.imshow('ped_img', img)
            else:
                print('没有检测到行人')

            print('cannot detect faces!')
            # cv2.imshow('img', img)
            if 0xFF & cv2.waitKey(5) == 27:
                break
            end = time.time()
            print("消耗时间：%f ms， count = %d" % ((end - start) * 1000, count))
            print('队列剩余长度：%d' % q.qsize())
            count += 1
            # capture.release()
            # cv2.destroyAllWindows()
    except KeyboardInterrupt:
        print('key interrupted , image process exit')
        exit()

if __name__ == '__main__':
    # q = Queue()
    # grab_proc = Process(target=grab, args=(q, camera['cross'],))
    # pro_proc = Process(target=process, args=(q,))
    # grab_proc.start()
    # pro_proc.start()

    q = queue.Queue(1000)
    grab_thread = threading.Thread(target=grab, args=(q, camera['cross'], 2))
    grab_thread.start()
    process(q)
