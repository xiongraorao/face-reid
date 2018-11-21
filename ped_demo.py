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
import argparse

import cv2
import numpy as np
import redis
from PIL import Image

from cluster.measure import Sample
from config import *
from util.pedestrian import Ped, grab
from util.face import face_feature, cosine, mat_to_base64

def redis_connect():
    pool = redis.ConnectionPool(host=args.redis_host, port=args.redis_port, db=args.db)
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


def process(q, args):
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
    ped_th = 0.8  # 判断行人是否为同一个的阈值
    person_threshold = 0.85  # ssd 中行人的置信分数
    resize_scale = args.resize_scale
    top_k = 10
    count = 0

    # initial ssd and reid
    ped = Ped(args)
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
            ped_result = ped.detect(img, person_threshold)
            ped_imgs = ped.crop(img, ped_result, False)

            for i,ped_img in enumerate(ped_imgs):
                ped_img_PIL = Image.fromarray(cv2.cvtColor(ped_img, cv2.COLOR_BGR2RGB))
                ped_feature = ped.extract_feature(ped_img_PIL).cpu().numpy().tolist()[0]
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
                    dire = args.save_dir + os.sep + c_name
                    if not os.path.exists(dire):
                        os.mkdir(dire)
                    cv2.imwrite(dire + os.sep + s_name + '.jpg', ped_img)

                else:
                    print('同一个行人，合并')
                    content = {'vector': feature, 'c_name': max_sim_cname, 'ped_vector': ped_feature}
                    r.set(s_name, json.dumps(content))
                    samples.append(Sample(s_name, feature, max_sim_cname, ped_feature))
                    dire = args.save_dir + os.sep + max_sim_cname
                    if not os.path.exists(dire):
                        os.mkdir(dire)
                    cv2.imwrite(dire + os.sep + s_name + '.jpg', ped_img)
                img = ped.visual(img, ped_result)
                cv2.imshow('ped_img', img)

            if len(ped_imgs) == 0:
                print('没有检测到行人')
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
    # 解析参数
    parser = argparse.ArgumentParser(description='which is used for pedestrian re-identification')
    parser.add_argument('--redis_host', '-rh', default=redis_host, help='redis host')
    parser.add_argument('--redis_port', '-rp', default=redis_port, help='redis port')
    parser.add_argument('--db', default=7, type=int, help='redis db')
    parser.add_argument('--camera', '-c', default=camera['cross'], help='camera rtsp address')
    parser.add_argument('--save_dir', '-s', default='/home/xrr/output2', help='which dir save grabbed pedestrian')
    parser.add_argument('--resize_scale', '-rs', default=1, type=int, help='grabbed image resize scale')
    parser.add_argument('--ped_th', default=0.8, type=float, help='pedestrian similarity threshold')
    parser.add_argument('--frame_rate', default=2, type=int, help='grab image rate frames/s ')
    parser.add_argument('--ssd_model', default='model/ssd300_mAP_77.43_v2.pth', help='ssd model path')
    parser.add_argument('--reid_model', default='reid/model/dense121/net_49.pth', help='reid model path')
    parser.add_argument('--gpu_id', type=int, default=0, help='gpu device number')
    parser.add_argument('--use_dense', action='store_true', help='use densenet121')
    parser.add_argument('--PCB', action='store_true', help='use PCB')
    args = parser.parse_args()

    q = queue.Queue(1000)
    grab_thread = threading.Thread(target=grab, args=(q, args.camera, args.frame_rate))
    grab_thread.start()
    process(q, args)
