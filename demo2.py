import base64
import time
import json
import os
import numpy as np

import cv2, redis, pdb

import cluster.measure as M
from cluster.measure import Sample, Cluster
from util.face import face_feature, get_list_files, cosine
from util import pedestrian as Ped
from PIL import Image

def redis_connect():
    pool = redis.ConnectionPool(host='192.168.1.11', port=6379, db=6)
    r = redis.Redis(connection_pool=pool)
    return r


#lfw_dir = "F:\\datasets\\lfw-sub"
lfw_dir = '/home/xrr/datasets/lfw-sub'

all_imgs = get_list_files(lfw_dir)
r = redis_connect()

# 初始化dataset

person_list = os.listdir(lfw_dir)

gt_clusters = []  # 真实的分类情况
pre_clusters = []  # 聚类的结果

for p in person_list:
    images = os.listdir(os.path.join(lfw_dir, p))
    samples = []
    for img in images:
        sample = Sample(os.path.join(lfw_dir, p, img), None, p)
        samples.append(sample)
    gt_clusters.append(Cluster(p, samples))


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
    r = redis_connect()
    # ids, features = get_all_feature()
    samples = get_all_feature2()
    up_th = 0.75  # 上阈值
    down_th = 0.6  # 下阈值
    ped_th = 0.9 # 行人特征阈值
    top_k = 10 # 取topk进行比较
    sum = len(all_imgs)
    start = time.clock()

    # samples_to_delete
    samples_to_delete = []

    # initial ssd and reid
    ssd_model, reid_model = Ped.init('model/ssd300_mAP_77.43_v2.pth', 'model/ft_ResNet50/net_last.pth')

    # 更新gt_cluster 的特征向量
    idx = 0
    for gtc_idx, gt_c in enumerate(gt_clusters):
        for gt_s in gt_c.samples:
            img = cv2.imread(gt_s.name)
            image = cv2.imencode('.jpg', img)[1]
            b = str(base64.b64encode(image))[2:-1]
            # feature = face.extract(b)
            faces = face_feature(b)
            face_num = len(faces['detect_info'])

            # pedestrian detection
            ped_result = Ped.detect(ssd_model, img)

            for i in range(face_num):
                feature = faces['feature'][i]
                gt_s.vector = feature

                # pedestrian crop
                ped_img = Ped.crop(img, ped_result, faces['detect_info'][i])
                ped_feature = []
                if len(ped_img) != 0:
                    cv2.imshow('ped_img', ped_img[0])
                    ped_img = Image.fromarray(cv2.cvtColor(ped_img[0], cv2.COLOR_BGR2RGB))
                    ped_feature = Ped.extract_feature(reid_model, ped_img).cpu().numpy().tolist()[0]
                gt_s.ped_vector = ped_feature

                # 和redis库里面的样本比对
                max_sim = -1.0
                max_sim_cname = -1.0
                max_sim_ped_vector = []

                if len(samples) != 0:
                    vectors = np.array([x.vector for x in samples])
                    sims = np.dot(vectors, np.array(feature).T) # n*1
                    sims = sims.reshape(-1,) # 变成一个一维数组
                    sims_top = np.argsort(-sims)[:top_k]
                    max_sim = sims[sims_top[0]]
                    max_sim_cname = samples[sims_top[0]].c_name
                    max_sim_ped_vector = samples[sims_top[0]].ped_vector

                if 0 < max_sim < down_th or len(samples) == 0:
                    # as a new cluster
                    content = {'vector': feature, 'c_name': gt_s.c_name, 'ped_vector': ped_feature}
                    # print('content ', content)
                    r.set(gt_s.name, json.dumps(content))
                    # add sample to memory
                    samples.append(Sample(gt_s.name, feature, gt_s.c_name, ped_feature))
                    print('单独成类, max_sim = %5f , c_name = %s ' % (max_sim, gt_s.c_name))
                elif max_sim < up_th:
                    # 中间阈值加上行人判断
                    print('consider pedestrian detection result...')

                    if len(ped_feature) == 0:
                        # 没有行人特征，认为创建新类
                        content = {'vector': feature, 'c_name': gt_s.c_name, 'ped_vector': ped_feature}
                        r.set(gt_s.name, json.dumps(content))
                        samples.append(Sample(gt_s.name, feature, gt_s.c_name, ped_feature))
                        print('===pedestrian===, max_sim = %5f , c_name = %s ' % (max_sim, gt_s.c_name))
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
                            r.set(gt_s.name, json.dumps(content))
                            samples.append(Sample(gt_s.name, feature, max_sim_cname, ped_feature))
                        else:
                            # 没有行人特征，认为创建新类
                            content = {'vector': feature, 'c_name': gt_s.c_name, 'ped_vector': ped_feature}
                            r.set(gt_s.name, json.dumps(content))
                            samples.append(Sample(gt_s.name, feature, gt_s.c_name, ped_feature))
                        print('===pedestrian===, max_sim = %5f , c_name = %s, max_ped_sim = %5f ' % (max_sim, max_sim_cname, ped_sim))
                else:
                    # remark c_name to the maximum similarity samples
                    content = {'vector': feature, 'c_name': max_sim_cname, 'ped_vector': ped_feature}
                    r.set(gt_s.name, json.dumps(content))
                    # add sample to memory
                    samples.append(Sample(gt_s.name, feature, max_sim_cname, ped_feature))
                    print('合并成类，max_sim = %5f , c_name = %s ' % (max_sim, max_sim_cname))
            if face_num == 0:
                # 删除 这个样本
                samples_to_delete.append((gtc_idx, gt_s))
                print("检测不到人脸=====")
            # img = estimate.pose(img)
            cv2.putText(img, str(idx) + '/' + str(sum), (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            cv2.imshow('img', img)
            idx += 1
            if 0xFF & cv2.waitKey(5) == 27:
                break

    # 保存 gt_cluster
    # f = open('./gt_cluster.txt', 'w')
    # f.write('[')
    # for c in gt_clusters:
    #     ss = '['
    #     for s in c.samples:
    #         ss += json.dumps(s, default=M.sample_2_json)
    #     ss += ']'
    #     content = "{'name':" + c.name + ", 'samples': " + ss + "}"
    #     f.write(content)
    # f.write(']')
    # f.close()
    # print('save gt_cluster done!')

    # 更新 gt_clusters , 把检测不到人脸的图片过滤掉

    for (c_i, s) in samples_to_delete:
        gt_clusters[c_i].samples.remove(s)

    # 更新 pre_cluster
    cluster_dic = {}
    for sample in samples:
        if sample.c_name in cluster_dic.keys():
            ss = cluster_dic[sample.c_name]
            ss.append(sample)
        else:
            cluster_dic[sample.c_name] = [sample]

    for key, value in cluster_dic.items():
        pre_clusters.append(Cluster(key, value))

    # 评价聚类结果
    print('clustering estimating ...')
    print('total cluster: ', len(pre_clusters))
    print('inner index: ')
    jaccard, fmi, ri = M.inner_index(gt_clusters, pre_clusters)
    print('jaccard index: %5f \nfmi index: %5f \nri index: %5f' % (jaccard, fmi, ri))
    # DBI= M.outer_index(pre_clusters)
    # print('outer index: ')
    # print('DBI index: %5f' % (DBI))

    end = time.clock()
    print("total time: %5f s " % (end - start))
    cv2.destroyAllWindows()
