import base64
import json
import os
import uuid

import cv2
import redis
import numpy as np

from util import face
from cluster.measure import Sample, Cluster
from util.face import face_feature, get_list_files, cosine
from util import pedestrian as Ped
from PIL import Image

# capture = cv2.VideoCapture("F:\iec.mp4")
# capture = cv2.VideoCapture("rtsp://admin:iec123456@192.168.1.71:554/unicast/c1/s0/live")
# capture = cv2.VideoCapture(0)
# capture = cv2.VideoCapture('rtsp://admin:iec123456@192.168.1.72:554/unicast/c1/s0/live')  # hk
# capture = cv2.VideoCapture('rtsp://admin:123456@192.168.1.61:554/h264/ch1/main/av_stream') # ys


#output_dir = "F:\\secretstar-id\\"
output_dir = '/home/xrr/output/'


def redis_connect():
    pool = redis.ConnectionPool(host='192.168.1.11', port=6379, db=5)
    r = redis.Redis(connection_pool=pool)
    return r


# def get_all_feature():
#     r = redis_connect()
#     keys = r.keys('*')
#     features = []
#     ids = []
#     for key in keys:
#         for i in r.smembers(key):
#             features.append(json.loads(i))
#             # ids.append(str(key))
#             ids.append(key)
#     return ids, features

def get_all_feature2():
    '''
    从redis数据库读取数据... 存储格式：key: 样本名，value: {'vector':[], 'c_name':''}
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


if __name__ == '__main__':
    # for i in range(0, 3000):
    #     ret, img = capture.read()
    #     print(i)
    r = redis_connect()

    # first load from redis
    samples = get_all_feature2()
    up_th = 0.75  # 上阈值
    down_th = 0.6  # 下阈值
    ped_th = 0.9
    frame_rate = 0.5  # 每秒抓一帧
    top_k = 10
    count = 0

    # initial ssd and reid
    ssd_model, reid_model = Ped.init('model/ssd300_mAP_77.43_v2.pth', 'model/ft_ResNet50/net_last.pth')

    while True:
        if int(count * frame_rate) % 25 == 0:
            ret, img = capture.read()
            count = 0
        else:
            count += 1
            continue
        if img is None:
            continue
        image = cv2.imencode('.jpg', img)[1]
        height, width = img.shape[:-1]
        b = str(base64.b64encode(image))[2:-1]
        # feature = face.extract(b)
        faces = face_feature(b)
        face_num = len(faces['detect_info'])

        ped_result = Ped.detect(ssd_model, img)

        # if feature is not None:
        for i in range(face_num):
            feature = faces['feature'][i]
            # coordinate = face.detect(b)
            # if coordinate.quality == 1 and coordinate.sideFace == 0 and coordinate.score > 0.95:
            detect_info = faces['detect_info'][i]
            if detect_info['quality'] == 1 and detect_info['sideFace'] == 0 and detect_info['score'] > 0.95:
                x = detect_info['x']
                y = detect_info['y']
                w = detect_info['w']
                h = detect_info['h']
                # 坐标修正
                x = 0 if x < 0 else x
                y = 0 if y < 0 else y
                h = height - y - 1 if y + h > height else  h
                w = width - x - 1 if x + w > width else w
                crop_img = img[y:y + h, x:x + w]

                # pedestrian crop
                ped_img = Ped.crop(img, ped_result, faces['detect_info'][i])
                ped_feature = []
                if len(ped_img) != 0:
                    cv2.imshow('ped_img', ped_img[0])
                    ped_img = Image.fromarray(cv2.cvtColor(ped_img[0], cv2.COLOR_BGR2RGB))
                    ped_feature = Ped.extract_feature(reid_model, ped_img).cpu().numpy().tolist()[0]

                # 和redis库里面所有的样本进行比对
                max_sim = -1.0
                max_sim_cname = -1.0
                max_sim_ped_vector = []
                c_name = str(uuid.uuid4())
                s_name = str(uuid.uuid4())

                if 0 < max_sim < up_th or len(samples) == 0:
                    # new id
                    content = {'vector': feature, 'c_name': c_name, 'ped_vector': ped_feature}
                    r.set(s_name, json.dumps(content))
                    samples.append(Sample(s_name, feature, c_name, ped_feature))
                    # features.append(feature)
                    # ids.append(str(random_id))
                    dire = output_dir + c_name
                    if not os.path.exists(dire):
                        os.mkdir(dire)
                    cv2.imwrite(dire + "\\" + s_name + ".jpg", crop_img)
                    print("生成新的id，并保存到redis", ", sim: ", max_sim)
                else:
                    vectors = np.array([x.vector for x in samples])
                    sims = np.dot(vectors, np.array(feature).T)
                    sims = sims.reshape(-1, )
                    sims_top = np.argsort(-sims)[:top_k]
                    max_sim = sims[sims_top[0]]
                    max_sim_cname = samples[sims_top[0]].c_name
                    max_sim_ped_vector = samples[sims_top[0]].ped_vector

                    if max_sim < up_th:
                        print('consider pedestrian detection result...')
                        c_name = str(uuid.uuid4())
                        s_name = str(uuid.uuid4())
                        if len(ped_feature) == 0:
                            # 没有检测到行人特征,创建新类
                            content = {'vector': feature, 'c_name': c_name, 'ped_vector': ped_feature}
                            r.set(s_name, json.dumps(content))
                            samples.append(Sample(s_name, feature, c_name, ped_feature))
                            print('===pedestrian===, max_sim = %5f , c_name = %s ' % (max_sim, c_name))
                        else:
                            ped_sim = 0
                            for i in sims_top:
                                if len(samples[i].ped_vector) != 0:
                                    max_sim_ped_vector = samples[i].ped_vector
                                    ped_sim = cosine(max_sim_ped_vector, ped_feature)
                                    break
                            if ped_sim > ped_th:
                                # 认为同一个人，合并
                                content = {'vector': feature, 'c_name': max_sim_cname, 'ped_vector': ped_feature}
                                r.set(s_name, json.dumps(content))
                                samples.append(Sample(s_name, feature, max_sim_cname, ped_feature))
                            else:
                                # 没有行人特征，认为创建新类
                                content = {'vector': feature, 'c_name': c_name, 'ped_vector': ped_feature}
                                r.set(s_name, json.dumps(content))
                                samples.append(Sample(s_name, feature, c_name, ped_feature))
                            print('===pedestrian===, max_sim = %5f , c_name = %s, max_ped_sim = %5f ' % (
                            max_sim, max_sim_cname, ped_sim))
                    else:
                        content = {'vector': feature, 'c_name': max_sim_cname, 'ped_vector': ped_feature}
                        r.set(s_name, json.dumps(content))
                        samples.append(Sample(s_name, feature, max_sim_cname, ped_feature))
                        # save img to folder
                        dire = output_dir + max_sim_cname
                        if not os.path.exists(dire):
                            os.mkdir(dire)
                        cv2.imwrite(dire + "\\" + max_sim_cname + ".jpg", crop_img)
                        print("匹配成功，并保存到redis", ", sim: ", max_sim)
                cv2.imshow('crop_img', crop_img)
            else:
                pass
        # img = cv2.resize(img, None, fx=0.3, fy=0.3, interpolation=cv2.INTER_CUBIC)
        cv2.imshow('img', img)
        if 0xFF & cv2.waitKey(5) == 27:
            break
    capture.release()
    cv2.destroyAllWindows()
