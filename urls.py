import json

import requests

data = [
    {'url': 'rtsp://100.98.0.240:8000/42012403001226746140_1', 'name': '龙城路锦绣龙城I区北二门右侧花坛', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012403001226797014_1', 'name': '郑桥小路当代国际花园西门', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012407001228416733_1', 'name': '碧桂园观澜小区东北门20栋中通快递正门花坛隔离带中', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012407001225348806_1', 'name': '碧桂园观澜小区东北门20栋中通快递正门花坛隔离带中-1', 'rate': 10},
    {'url': 'rtsp://100.98.0.240:8000/42012407001226671530_1', 'name': '碧桂园左岸小区1栋路口', 'rate': 10}
]

headers = {'content-type': "application/json"}


def add(url):
    for d in data:
        response = requests.post(url, data=json.dumps(d), headers=headers)
        print(response.json())

# add('http://100.98.10.55:5000/camera/add')
add('http://192.168.1.6:5000/camera/add')
