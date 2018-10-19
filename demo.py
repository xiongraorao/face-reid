import base64
import json
import os
import uuid

import cv2
import redis

from util import face

#capture = cv2.VideoCapture("F:\iec.mp4")
capture = cv2.VideoCapture("rtsp://admin:iec123456@192.168.1.71:554/unicast/c1/s0/live")
capture = cv2.VideoCapture(0)
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
            #ids.append(str(key))
            ids.append(key)
    return ids, features


if __name__ == '__main__':
    # for i in range(0, 3000):
    #     ret, img = capture.read()
    #     print(i)
    r = redis_connect()

    # first load from redis
    ids, features = get_all_feature()
    up_th = 0.7 # 上阈值
    frame_rate = 0.5  # 每秒抓一帧
    count = 0
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
        b = str(base64.b64encode(image))[2:-1]
        feature = face.extract(b)

        if feature is not None:
            coordinate = face.detect(b)
            crop_img = img[coordinate.y:coordinate.y + coordinate.height, coordinate.x:coordinate.x + coordinate.width]
            # 和redis库里面所有的样本进行比对
            max_sim = -1.0
            max_sim_id = -1.0
            for idx, val in enumerate(features):
                similarity = face.cosine(feature, val)
                if similarity < max_sim:
                    continue
                else:
                    max_sim = similarity
                    max_sim_id = ids[idx]
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
        #img = cv2.resize(img, None, fx=0.3, fy=0.3, interpolation=cv2.INTER_CUBIC)
        cv2.imshow('img', img)
        if 0xFF & cv2.waitKey(5) == 27:
            break
    capture.release()
    cv2.destroyAllWindows()
