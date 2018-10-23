from demo import redis_connect, get_all_feature
from util import face
import uuid, json, base64, cv2, os, datetime
import face_pose_estimate as estimate

lfw_dir = "F:\\datasets\\lfw"
output_dir = "F:\\lfw-id\\"

all_imgs = face.get_list_files(lfw_dir)
r = redis_connect()

if __name__ == '__main__':
    r = redis_connect()
    ids, features = get_all_feature()
    up_th = 0.7  # 上阈值
    frame_rate = 0.5  # 每秒抓一帧
    sum = len(all_imgs)
    start = datetime.datetime.now()
    for idx,img in enumerate(all_imgs):
        img = cv2.imread(img)
        image = cv2.imencode('.jpg', img)[1]
        b = str(base64.b64encode(image))[2:-1]
        feature = face.extract(b)

        if feature is not None:
            coordinate = face.detect(b)
            if coordinate.quality == 1 and coordinate.sideFace == 0 and coordinate.score > 0.95:
                crop_img = img[coordinate.y:coordinate.y + coordinate.height,
                           coordinate.x:coordinate.x + coordinate.width]
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
                    print("生成新的id，并保存到redis", ", sim: ", max_sim , ", count= " , idx)
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
                    print("匹配成功，并保存到redis", ", sim: ", max_sim , ", count= " , idx)
            else:
                pass
        else:
            pass
        # img = cv2.resize(img, None, fx=0.3, fy=0.3, interpolation=cv2.INTER_CUBIC)
        img = estimate.pose(img)
        cv2.putText(img, str(idx)+'/' + str(sum), (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5,(255,0,0),2 )
        cv2.imshow('img', img)
        if 0xFF & cv2.waitKey(5) == 27:
            break
    end = datetime.datetime.now()
    print("total time:", str((end-start)/1000) + 's')
    cv2.destroyAllWindows()

