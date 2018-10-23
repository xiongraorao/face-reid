from flask import Flask, render_template, request, redirect,url_for
from demo import redis_connect
import os
import base64

app = Flask(__name__, static_url_path='')

r = redis_connect()


def visualize():
    app.run(host="localhost", port="8888")


@app.route('/', methods=['GET'])
def index():
    keys = r.keys('*')
    clusters = []
    for key in keys:
        clusters.append(key.decode('utf-8'))
    for c in clusters:
        print(c)
    return render_template('clusters.html', clusters=clusters)


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
    keys = r.keys('*')
    clusters = [[]]
    cluster = []
    for key in keys:
        cluster.append(key.decode('utf-8'))
        img_file_list = read_image(key.decode('utf-8'))
        img_list = []
        for file in img_file_list:
            f = open(file, 'rb')
            b = 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode('utf-8')
            img_list.append(b)
        clusters.append(img_list)
    clusters = clusters[1:]
    #print('cluster len: ' ,len(cluster) , 'clusters len: ' , len(clusters))
    #clusters = dict(zip(cluster, clusters))
    return render_template('all.html', clusters=clusters, cluster=cluster)

def read_image(cluster_id):
    basedir = "F:\\lfw-id\\" + cluster_id
    l = os.listdir(basedir)
    ret = []
    for i in l:
        ret.append(os.path.join(basedir, i))
    return ret


if __name__ == '__main__':
    visualize()
