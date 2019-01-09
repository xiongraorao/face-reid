import json
import time

import requests

data = [
    {'url': 'rtsp://100.98.0.240:8000/42012403001226746140_1', 'name': '龙城路锦绣龙城I区北二门右侧花坛', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012403001226797014_1', 'name': '郑桥小路当代国际花园西门', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012407001228416733_1', 'name': '碧桂园观澜小区东北门20栋中通快递正门花坛隔离带中', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012407001225348806_1', 'name': '碧桂园观澜小区东北门20栋中通快递正门花坛隔离带中-1', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012407001226671530_1', 'name': '碧桂园左岸小区1栋路口', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012410001226480627_1', 'name': '楚平路刘家咀还建小区2', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012410001226486202_1', 'name': '楚平路刘家咀还建小区3', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012401001222334432_1', 'name': '717小区北门', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012401001229475088_1', 'name': '717小区北门-1', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012407001225396795_1', 'name': '花城汇西湖景门口-1', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012407001225592104_1', 'name': '幸福大街竹园17栋入口-1', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012407001225725571_1', 'name': '花山青年城二期北门', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012407001225616375_1', 'name': '碧桂园三湖涧三号门9栋对面-1', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012407001225749996_1', 'name': '花山青年城二期8号楼出入口', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012439001225404771_1', 'name': '高新二路关南小区门口', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012439001224287595_1', 'name': '珞瑜东路-康居园小区大门口', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012439001221057356_1', 'name': '珞瑜东路-新嘉园小区门口', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012439001221941742_1', 'name': '光谷一路关山新村还建小区', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012439001225904331_1', 'name': '凌家山北路-格调小区门前南', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012439001229636809_1', 'name': '珞瑜东路武缝小区交界处', 'rate': 10}
]

data2 = [
    {'url': 'rtsp://admin:iec123456@192.168.1.71:554/unicast/c1/s0/live', 'name': '开发室', 'rate': 10},
    {'url': 'rtsp://admin:iec123456@192.168.1.72:554/unicast/c1/s0/live', 'name': '十字路口', 'rate': 10},
    {'url': 'rtsp://admin:123456@192.168.1.62:554/h264/ch1/main/av_stream', 'name': '一楼大厅', 'rate': 10},
    {'url': 'rtsp://admin:123456@192.168.1.63:554/h264/ch1/main/av_stream', 'name': '7楼电梯口1', 'rate': 10},
    {'url': 'rtsp://admin:123456@192.168.1.64:554/h264/ch1/main/av_stream', 'name': '7楼电梯口2', 'rate': 10},
    {'url': 'rtsp://admin:123456@192.168.1.65:554/h264/ch1/main/av_stream', 'name': '公司门口', 'rate': 10},
    {'url': 'rtsp://admin:123456@192.168.1.66:554/h264/ch1/main/av_stream', 'name': '产品部演示系统', 'rate': 10},
    {'url': 'rtsp://admin:123456@192.168.1.67:554/h264/ch1/main/av_stream', 'name': '公司大厅', 'rate': 10},
    {'url': 'rtsp://admin:123456@192.168.1.68:554/h264/ch1/main/av_stream', 'name': '过道', 'rate': 10},
    {'url': 'rtsp://admin:123456@192.168.1.69:554/h264/ch1/main/av_stream', 'name': '会议室演示系统', 'rate': 10},
    {'url': 'rtsp://admin:123456@192.168.1.70:554/h264/ch1/main/av_stream', 'name': '会议室', 'rate': 10}
]

headers = {'content-type': "application/json"}


def post(url):
    for d in data2:
        response = requests.post(url, data=json.dumps(d), headers=headers)
        print(response.json())
        # time.sleep(5)


# post('http://100.98.10.55:5000/camera/add')
# post('http://192.168.1.6:5000/camera/add')

def cam_del(ids):
    # url = 'http://100.98.10.55:5000/camera/del'
    url = 'http://192.168.1.6:5000/camera/del'
    for id in ids:
        response = requests.post(url, data=json.dumps({'id': id}), headers=headers)
        print(response.json())

# cam_del([1,2,3,4,5])

def status(id):
    url = 'http://192.168.1.6:5000/camera/status'
    response = requests.post(url, data=json.dumps({'id': id}), headers=headers)
    print(response.json())

status(1)

# cam_del(list(range(1,22)))
cam_del([22])

