from flask import Flask, render_template, request, redirect, url_for
import os
import base64
import json
import redis
from config import *
import argparse

parser = argparse.ArgumentParser(description='which is used for visualizating cluster result')
parser.add_argument('--redis_host', '-rh', default=redis_host, help='redis host')
parser.add_argument('--redis_port', '-rp', default=redis_port, help='redis port')
parser.add_argument('--db', required=True, type=int, help='redis db')
parser.add_argument('--dir', '-d', help='image base dir', default='/home/xrr/output')
parser.add_argument('--host', default='192.168.1.6', help='web service host')
parser.add_argument('--port', '-p', default=8888, help='web service port')
args = parser.parse_args()

app = Flask(__name__, static_url_path='')


def redis_connect(db):
    pool = redis.ConnectionPool(host=args.redis_host, port=args.redis_port, db=db)
    r = redis.Redis(connection_pool=pool)
    return r

base_dir = args.dir
db = args.db
r = redis_connect(db)


def visualize():
    app.run(host=args.host, port=args.port)


def get_clusters():
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
        sample_path = os.path.join(base_dir, content['c_name'], key.decode('utf-8') + '.jpg')
        if content['c_name'] in clusters:
            clusters[content['c_name']].append(sample_path)
        else:
            clusters[content['c_name']] = [sample_path]
    return clusters


@app.route('/set', methods=['POST'])
def set_para():
    '''
    设置redis 数据库和图片的路径
    :return:
    '''
    global base_dir, r, db
    base_dir = request.form['base_dir']
    db = request.form['db']
    r = redis_connect(db)
    print('set parameters: ', base_dir, db)
    return redirect(url_for('index'))


@app.route('/', methods=['GET'])
def index():
    ret = get_clusters()
    clusters = [x for x in ret.keys()]
    return render_template('clusters.html', clusters=clusters, size=len(clusters), dir = base_dir, db = db)


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
    del_dirs = []
    for key in r.keys('*'):
        content = r.get(key)
        content = json.loads(content.decode('utf-8'))
        r.delete(key)
        del_file = os.path.join(base_dir, content['c_name'], key.decode('utf-8') + '.jpg')
        if os.path.exists(del_file):
            os.remove(del_file)
            print('delete success!===', del_file)
        del_dirs.append(os.path.join(base_dir, content['c_name']))
    for d in set(del_dirs):
        print('to be delete dirs: ', d)
        if not os.listdir(d):  # c_name 目录为空就删除
            os.removedirs(d)
            print('delete cluster name directory！===', os.path.join(base_dir, content['c_name']))
    print('delet all cluster!')
    return redirect(url_for('index'))


@app.route('/del', methods=['GET'])
def delete_one():
    cluster_id = request.args.get('id', '')
    print('delete id = ', id)
    for key in r.keys('*'):
        content = r.get(key)
        content = json.loads(content.decode('utf-8'))
        if cluster_id == content['c_name']:
            r.delete(key)
            del_file = os.path.join(base_dir, content['c_name'], key.decode('utf-8') + '.jpg')
            if os.path.exists(del_file):
                os.remove(del_file)
                print('delete success!===', del_file)
    if not os.listdir(os.path.join(base_dir, content['c_name'])):
        os.removedirs(os.path.join(base_dir, content['c_name']))
        print('delete cluster name directory!===', os.path.join(base_dir, content['c_name']))
    return redirect(url_for('index'))


@app.route('/all', methods=["GET"])
def all():
    clusters = [[]]
    ret = get_clusters()
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
    clusters = get_clusters()
    return clusters[cluster_id]


if __name__ == '__main__':
    visualize()
