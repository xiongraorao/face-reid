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

capture = cv2.VideoCapture("F:\iec.mp4")
# capture = cv2.VideoCapture("rtsp://admin:iec123456@192.168.1.71:554/unicast/c1/s0/live")
# capture = cv2.VideoCapture(0)
output_dir = "F:\\secretstar-id\\"


def redis_connect():
    pool = redis.ConnectionPool(host='192.168.1.11', port=6379, db=5)
    r = redis.Redis(connection_pool=pool)
    return r


def get_all_feature():
    r = redis_connect()
    keys = r.keys('*')
    features = []
    ids = []
    for key in keys:
        for i in r.smembers(key):
            features.append(json.loads(i))
            # ids.append(str(key))
            ids.append(key)
    return ids, features


if __name__ == '__main__':
    # for i in range(0, 3000):
    #     ret, img = capture.read()
    #     print(i)
    r = redis_connect()

    # first load from redis
    ids, features = get_all_feature()
    up_th = 0.75  # 上阈值
    down_th = 0.6  # 下阈值
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
                max_sim_id = -1.0

                if len(features) != 0:
                    vectors = np.array(features)
                    sims = np.dot(features, np.array(feature).T)
                    sims = sims.reshape(-1,)
                    sim_top = np.argsort(-sims)[:top_k]
                    max_sim = sims[sim_top[0]]
                    max_sim_id = ids[sim_top[0]]

                if 0 < max_sim < up_th or len(features) == 0:
                    # new id
                    random_id = uuid.uuid1()
                    r.sadd(str(random_id), json.dumps(feature))
                    features.append(feature)
                    ids.append(str(random_id))
                    dire = output_dir + str(random_id)
                    if not os.path.exists(dire):
                        os.mkdir(dire)
                    cv2.imwrite(dire + "\\" + str(uuid.uuid1()) + ".jpg", crop_img)
                    print("生成新的id，并保存到redis", ", sim: ", max_sim)
                elif max_sim < up_th:

                    print('consider pedestrian detection result...')

                    if len(ped_feature) == 0:
                        # 没有检测到行人特征



                else:
                    # add in maximum feature list
                    r.sadd(str(max_sim_id), json.dumps(feature))
                    # add in features, in memory
                    features.append(feature)
                    ids.append(str(max_sim_id))
                    # save img to folder
                    dire = output_dir + str(max_sim_id)
                    if not os.path.exists(dire):
                        os.mkdir(dire)
                    cv2.imwrite(dire + "\\" + str(uuid.uuid1()) + ".jpg", crop_img)
                    print("匹配成功，并保存到redis", ", sim: ", max_sim)
            else:
                pass
        else:
            pass
        # img = cv2.resize(img, None, fx=0.3, fy=0.3, interpolation=cv2.INTER_CUBIC)
        img = estimate.pose(img)
        cv2.imshow('img', img)
        if 0xFF & cv2.waitKey(5) == 27:
            break
    capture.release()
    cv2.destroyAllWindows()
