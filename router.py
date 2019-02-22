from flask import Flask, request
from werkzeug.routing import BaseConverter
import json
import requests
import configparser
from kazoo.client import KazooClient
import time

# 自定义转换器
class RegexConverter(BaseConverter):
    def __init__(self, url_map, *args):
        super(RegexConverter, self).__init__(url_map)
        self.regex = args[0] # 将接受的第1个参数当作匹配规则进行保存

# 路由类
class Router():
    def __init__(self): # 初始化
        self.socket = "192.168.1.6:1234"
        self.headers = {'content-type': "application/json"}
        self.socketsList = [] # sockets 列表
        self.curSocketIndex = -1 # sockets 列表的下标，当前使用的 socket，-1 表示使用默认值，-2 表示不可用
        self.layersList = [] # layers 列表
        self.zkNodeTimeOut = 6 # znode 超时时间，单位 s
        self.zkNodeDropTimeOut = 86400 # znode 超时过长时间就抛弃，单位 s
        self.socketsListTryLoop = 5 # socketsList 循环尝试数

        # 读配置文件
        self.config = configparser.ConfigParser()
        self.config.read("./router.config")
        
        self.conZookeeper() # 连接 zookeeper

        self.refreshSocketsList() # 刷新 sockets 列表

        self.refreshLayersList() # 刷新 layers 列表

    def refreshSocketsList(self): # 刷新 sockets 列表
        self.socketsList = self.zk.get_children("/router")

    def refreshSocket(self): # 刷新 socket
        if len(self.socketsList) == 0 or self.socketsList[0] == '': # sockets 列表为空时无变化
            self.socket = "192.168.1.6:1234"
            self.curSocketIndex = -2
            return
        curSocketIndex = self.curSocketIndex # 复制
        socketsList = self.socketsList[:] # 复制
        c = len(socketsList) * self.socketsListTryLoop
        tmpSocketIndex = curSocketIndex
        while c > 0:
            tmpSocketIndex += 1
            if tmpSocketIndex >= len(socketsList): # 循环
                tmpSocketIndex = 0
            if self.zk.exists("/router/"+socketsList[tmpSocketIndex]):
                data, stat = self.zk.get("/router/"+socketsList[tmpSocketIndex])
                if time.time() - stat.mtime / 1000 > self.zkNodeTimeOut: # socket 超时
                    if time.time() - stat.mtime / 1000 > self.zkNodeDropTimeOut: # socket 严重超时
                        self.zk.delete("/router/"+socketsList[tmpSocketIndex])
                    c -= 1
                else:
                    self.socket = socketsList[tmpSocketIndex]
                    self.curSocketIndex = tmpSocketIndex
                    break
            else:
                c -= 1
        if c == 0:
            self.socket = "192.168.1.6:1234"
            self.curSocketIndex = -2

    def refreshLayersList(self): # 刷新 layers 列表
        layers_mix = self.config.get("layers","layers_mix")
        self.layersList = layers_mix.split(",")

    def conZookeeper(self): # 连接 zookeeper
        self.zk = KazooClient(self.config.get("zoo1","hosts")) # zookeeper
        self.zk.start()
        self.zk.ensure_path("/router")

    def disconZookeeper(self): # 断开与 zookeeper 的连接
        self.zk.stop()


app = Flask(__name__)
app.url_map.converters["re"] = RegexConverter # 将自定义转换器添加到转换器字典中，并指定转换器使用时名字为: re

router = Router() # 路由实例

# 监听 znode /router/...
@router.zk.ChildrenWatch("/router")
def watchChildren(childrenList):
    if len(childrenList) == 0: # sockets 全下线
        print("no sockets")
        router.socketsList = []
        router.socket = "192.168.1.6:1234"
        router.curSocketIndex = -2
        return
    eqList = [val for val in router.socketsList if val in childrenList]
    sOnlyList = [val for val in router.socketsList if val not in childrenList]
    cOnlyList = [val for val in childrenList if val not in router.socketsList]
    if len(sOnlyList) == 0 and len(cOnlyList) == 0: # sockets 无变化
        print("no change")
        return
    if router.curSocketIndex >= 0 and router.socketsList[router.curSocketIndex] in eqList:
        router.curSocketIndex = eqList.index(router.socketsList[router.curSocketIndex])
        router.socketsList = eqList.extend(cOnlyList)
    else:
        router.socketsList = eqList + cOnlyList
        router.curSocketIndex = -1
    print(router.socketsList, router.curSocketIndex)

# 路由 匹配
@app.route("/<re('([a-zA-Z\d_](/[a-zA-Z\d_])*)*'):layers>",methods=["POST","GET"])
def viewFunction(layers):
    errRet = {'time_used': 0, 'rtn': -1, 'id': -1, 'message': ''}
    if layers not in router.layersList: # 未在配置中
        errRet["message"] = "not found 404"
        return json.dumps(errRet)
    else:
        router.refreshSocket() # 刷新 socket
        if router.curSocketIndex < 0: # 无可用 socket
            errRet["message"] = "no useful socket"
            return json.dumps(errRet)
        try:
            socket = router.socket # 复制
            if request.method == "POST":
                r = requests.post("http://"+socket+"/"+layers,data=request.get_data(),headers=router.headers)
                return "From "+socket+": "+r.text
            elif request.method == "GET":
                r = requests.get("http://"+socket+"/"+layers,data=request.get_data(),headers=router.headers)
                return "From "+socket+": "+r.text
            else:
                errRet["message"] = "method not support"
                return json.dumps(errRet)
        except requests.exceptions.ConnectionError:
            errRet["message"] = "connection error"
            return json.dumps(errRet)

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=9000)
    router.disconZookeeper() # 断开与 zookeeper 的连接




