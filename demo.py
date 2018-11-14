import json
import os
import time
import uuid
from multiprocessing import Process, Queue

import cv2
import numpy as np
import redis
from PIL import Image

from cluster.measure import Sample
from config import *
from util import pedestrian as Ped
from util.face import face_feature, cosine, mat_to_base64


def redis_connect():
    pool = redis.ConnectionPool(host=redis_host, port=redis_port, db=redis_db)
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


def grab(q, url):
    '''
    抓图
    :param q:
    :return:
    '''
    capture = cv2.VideoCapture(url)
    count = 0
    frame_rate = 2  # 每秒抓几帧
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
            print('grab %d image' % count)
            count += 1
    except KeyboardInterrupt:
        print('key interrupted , grab process exit')
        exit()

def grab2(q, url):
    '''
    抓图, 该种方法运行一段时间就会卡死
    :param q:
    :return:
    '''
    capture = cv2.VideoCapture(url)
    count = 0
    frame_rate = 1
    try:
        while True:
            time.sleep(1.0/frame_rate)
            ret, img = capture.read()
            if ret is True:
                q.put(img)
                print('grab %d image' % count)
                count += 1
    except KeyboardInterrupt:
        print('key interrupted , grab process exit')
        exit(1)

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
    ped_th = 0.9
    resize_scale = 0.5
    top_k = 10
    count = 0

    # initial ssd and reid
    ssd_model, reid_model = Ped.init('model/ssd300_mAP_77.43_v2.pth', 'model/ft_ResNet50/net_last.pth', gpu_id)

    print('start process images')
    try:
        while True:
            start = time.time()
            img = q.get()
            img = cv2.resize(img, None, fx=resize_scale, fy=resize_scale, interpolation=cv2.INTER_CUBIC)
            height, width = img.shape[:-1]
            b = mat_to_base64(img)
            faces = face_feature(b)
            face_num = len(faces['detect_info'])
            ped_result = Ped.detect(ssd_model, img)

            for i in range(face_num):
                feature = faces['feature'][i]
                detect_info = faces['detect_info'][i]
                if detect_info['quality'] == 1 and detect_info['sideFace'] == 0 and detect_info['score'] > 0.95:
                    x = detect_info['x']
                    y = detect_info['y']
                    w = detect_info['w']
                    h = detect_info['h']
                    # 坐标修正
                    x = 0 if x < 0 else x
                    y = 0 if y < 0 else y
                    h = height - y - 1 if y + h > height else h
                    w = width - x - 1 if x + w > width else w
                    crop_img = img[y:y + h, x:x + w]

                    # pedestrian crop
                    ped_img = Ped.crop(img, ped_result, faces['detect_info'][i])
                    ped_feature = []
                    if len(ped_img) != 0:
                        # cv2.imshow('ped_img', ped_img[0])
                        ped_img = Image.fromarray(cv2.cvtColor(ped_img[0], cv2.COLOR_BGR2RGB))
                        ped_feature = Ped.extract_feature(reid_model, ped_img).cpu().numpy().tolist()[0]

                    # 和redis库里面所有的样本进行比对
                    max_sim = -1.0
                    max_sim_cname = 'MAX_CNAME'
                    max_sim_ped_vector = []

                    if len(samples) > 0:
                        vectors = np.array([x.vector for x in samples])
                        sims = np.dot(vectors, np.array(feature).T).reshape(-1, )
                        sims_top = np.argsort(-sims)[:top_k]
                        max_sim = sims[sims_top[0]]
                        max_sim_cname = samples[sims_top[0]].c_name
                        max_sim_ped_vector = samples[sims_top[0]].ped_vector

                    # 为新生成的ID做准备
                    c_name = str(uuid.uuid4())
                    s_name = str(uuid.uuid4())

                    if 0 < max_sim < down_th or max_sim == -1.0:
                        # new id
                        content = {'vector': feature, 'c_name': c_name, 'ped_vector': ped_feature}
                        r.set(s_name, json.dumps(content))
                        samples.append(Sample(s_name, feature, c_name, ped_feature))
                        dire = output_dir + os.sep + c_name
                        if not os.path.exists(dire):
                            os.mkdir(dire)
                        cv2.imwrite(dire + os.sep + s_name + '.jpg', crop_img)
                        print("生成新的id，并保存到redis , sim=%f, s_name=%s" % (max_sim, s_name))
                    else:
                        # need to classify
                        if down_th < max_sim < up_th:
                            print('consider pedestrian detection result...')
                            if len(ped_feature) == 0:
                                # 没有检测到行人特征,创建新类
                                content = {'vector': feature, 'c_name': c_name, 'ped_vector': ped_feature}
                                r.set(s_name, json.dumps(content))
                                samples.append(Sample(s_name, feature, c_name, ped_feature))
                                dire = output_dir + os.sep + c_name
                                if not os.path.exists(dire):
                                    os.mkdir(dire)
                                cv2.imwrite(dire + os.sep + s_name + '.jpg', crop_img)
                                print('没有检测到行人，创建新类, max_sim = %5f , c_name = %s, s_name = %s ' % (max_sim, c_name, s_name))
                            else:
                                ped_sim = 0.0
                                for i in sims_top:
                                    if len(samples[i].ped_vector) != 0:
                                        max_sim_ped_vector = samples[i].ped_vector
                                        ped_sim = cosine(max_sim_ped_vector, ped_feature)
                                        break
                                if ped_sim > ped_th:
                                    # 行人相似度高于阈值，认为同一个人，合并
                                    content = {'vector': feature, 'c_name': max_sim_cname, 'ped_vector': ped_feature}
                                    r.set(s_name, json.dumps(content))
                                    samples.append(Sample(s_name, feature, max_sim_cname, ped_feature))
                                    dire = output_dir + os.sep + max_sim_cname
                                    if not os.path.exists(dire):
                                        os.mkdir(dire)
                                    cv2.imwrite(dire + os.sep + s_name + '.jpg', crop_img)
                                    print('行人相似度高于阈值，合并, max_sim = %5f , c_name = %s, max_ped_sim = %5f, s_name = %s' % (
                                        max_sim, max_sim_cname, ped_sim, s_name))
                                else:
                                    # 行人相似度低于阈值，认为创建新类
                                    content = {'vector': feature, 'c_name': c_name, 'ped_vector': ped_feature}
                                    r.set(s_name, json.dumps(content))
                                    samples.append(Sample(s_name, feature, c_name, ped_feature))
                                    dire = output_dir + os.sep + c_name
                                    if not os.path.exists(dire):
                                        os.mkdir(dire)
                                    cv2.imwrite(dire + os.sep + s_name + '.jpg', crop_img)
                                    print('行人相似度低于阈值，创建新类, max_sim = %5f , c_name = %s, max_ped_sim = %5f, s_name = %s' % (
                                        max_sim, max_sim_cname, ped_sim, s_name))
                        else:
                            # 同一个人
                            content = {'vector': feature, 'c_name': max_sim_cname, 'ped_vector': ped_feature}
                            print()
                            r.set(s_name, json.dumps(content))
                            samples.append(Sample(s_name, feature, max_sim_cname, ped_feature))
                            dire = output_dir + os.sep + max_sim_cname
                            if not os.path.exists(dire):
                                os.mkdir(dire)
                            cv2.imwrite(dire + os.sep + s_name + '.jpg', crop_img)
                            print("匹配成功，并保存到redis, sim = %f, c_name = %s, s_name = %s" % (max_sim, max_sim_cname, s_name))
                            # cv2.imshow('crop_img', crop_img)
                else:
                    print('检测到的人脸质量不佳')
                    pass
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
    q = Queue()
    grab_proc = Process(target=grab, args=(q, camera['cross'],))
    pro_proc = Process(target=process, args=(q,))
    grab_proc.start()
    pro_proc.start()
