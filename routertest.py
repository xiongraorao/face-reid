import requests
import json
from kazoo.client import KazooClient
import time

if __name__ == "__main__":
    data_request = {"id":"1","rate":"2"}
    headers = {'content-type': "application/json"}
    #print('request parmas: ', json.dumps(data_request, ensure_ascii=False))
    r = requests.post("http://192.168.1.6:9000/camera/add",data=json.dumps(data_request), headers=headers)
    print(r.text)
    r = requests.post("http://192.168.1.6:9000/camera/del",data={"param":"test"})
    print(r.text)
    #r = requests.get("http://192.168.1.6:9000/camera/list",data={"param":"test"})
    #print(r.text)

    zk = KazooClient(hosts="192.168.1.6:21181")
    zk.start()
    #zk.ensure_path("/router/192.168.1.6:5000")
    #zk.delete("/router/192.168.1.6:5000")
    #zk.set("/router/192.168.1.6:5000",str(time.time()).encode())
    zk.stop()
