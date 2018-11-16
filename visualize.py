from flask import Flask, render_template, request, redirect,url_for
from demo import redis_connect
import os
import base64
import json

import pdb
app = Flask(__name__, static_url_path='')

r = redis_connect()
base_dir = '/home/xrr/output'

def visualize():
    app.run(host="192.168.1.6", port="8888")

def get_clusters(dir_base):
    '''
    得到cluster和samples的路径
    @:param dir_base 图片基础目录
    :return:
    '''
    samples = r.keys('*')
    clusters = {}
    for key in samples:
        content = r.get(key)
        content = json.loads(content.decode('utf-8'))
        sample_path = os.path.join(dir_base, content['c_name'], key.decode('utf-8') + '.jpg')
        if content['c_name'] in clusters:
            clusters[content['c_name']].append(sample_path)
        else:
            clusters[content['c_name']] = [sample_path]
    return clusters

@app.route('/', methods=['GET'])
def index():
    # keys = r.keys('*')
    # clusters = []
    # for key in keys:
    #     clusters.append(key.decode('utf-8'))
    # for c in clusters:
    #     print(c)
    ret = get_clusters(base_dir)
    clusters = [x for x in ret.keys()]
    return render_template('clusters.html', clusters=clusters, size=len(clusters))


@app.route('/cluster', methods=['GET'])
def cluster():
    id = str(request.args.get('id', ''))
    # read from disk and render in single_cluster page
    # return img list
    img_file_list = read_image(id)
    img_list = []
    for file in img_file_list:
        f = open(file, 'rb')
        b = 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode('utf-8')
        img_list.append(b)
    return render_template('single_cluster.html', img_list=img_list)

@app.route('/delete', methods=["GET"])
def delete():
    for key in r.keys('*'):
        r.delete(key)
    print('delet all cluster!')
    return redirect(url_for('index'))

@app.route('/all', methods=["GET"])
def all():
    # keys = r.keys('*')
    # clusters = [[]]
    # cluster = []

    # for key in keys():
    #     cluster.append(key.decode('utf-8'))
    #     img_file_list = read_image(key.decode('utf-8'))
    #     img_list = []
    #     for file in img_file_list:
    #         f = open(file, 'rb')
    #         b = 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode('utf-8')
    #         img_list.append(b)
    #     clusters.append(img_list)
    # clusters = clusters[1:]
    # #print('cluster len: ' ,len(cluster) , 'clusters len: ' , len(clusters))
    # #clusters = dict(zip(cluster, clusters))

    clusters = [[]]
    ret = get_clusters(base_dir)
    cluster = ret.keys()
    for key in cluster:
        img_list = []
        for file_name in ret[key]:
            f = open(file_name, 'rb')
            b = 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode('utf-8')
            img_list.append(b)
        clusters.append(img_list)
    clusters.pop(0)

    return render_template('all.html', clusters=clusters, cluster=cluster)

def read_image(cluster_id):
    clusters = get_clusters(base_dir)
    return clusters[cluster_id]


if __name__ == '__main__':
    visualize()
