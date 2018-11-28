import requests

class WeedMaster():
    def __init__(self, host='127.0.0.1', port=9333):
        self.host = host
        self.port = port

    def assign(self, replication='000', count=1, dataCenter=None):
        '''
        get assigned key
        :param replication:
        :param count: keep many reserve(multi-version)
        :return:
        {'fid': '1,04bdb7f514', 'url': '192.168.1.6:38080', 'publicUrl': '192.168.1.6:38080', 'count': 1}
        '''
        url = 'http://' + self.host + ':' + str(self.port) + '/dir/assign'
        params = {'replication': replication, 'count':count}
        if dataCenter is not None:
            params['dataCenter'] = dataCenter
        res = requests.get(url, params=params)
        return res.json()

    def lookup(self, fid):
        '''
        look up whether the volums had been moved
        :param fid: file id
        :return:
        {'volumeId': '7', 'locations': [{'url': '192.168.1.6:38080', 'publicUrl': '192.168.1.6:38080'}]}
        {'volumeId': '17', 'error': 'volumeId 17 not found.'}
        '''
        url = 'http://' + self.host + ':' + str(self.port) + '/dir/lookup'
        params = {'volumeId': fid}
        res = requests.get(url, params=params)
        return res.json()

    def allocate(self, replication='000', count = 1,  collection=None, dataCenter = None, ttl = None):
        '''
        pre-allocate new volumes
        :param replication:
        :param count:
        :param collection:
        :param dataCenter:
        :param ttl: keep alive time
        :return:
        '''
        url = 'http://' + self.host + ':' + str(self.port) + '/vol/grow'
        params = {'replication': replication, 'count': count}
        if collection is not None:
            params['collection'] = collection
        if dataCenter is not None:
            params['dataCenter'] = dataCenter
        if ttl is not None:
            params['ttl'] = ttl
        res = requests.get(url, params=params)
        return res.json()

    def collect_del(self, collection):
        url = 'http://' + self.host + ':' + str(self.port) + '/col/delete'
        res = requests.get(url, params={'collection':collection})
        return res.json()

    def status(self):
        '''
        check status
        :return:
        '''
        url = 'http://' + self.host + ':' + str(self.port) + '/cluster/status'
        res = requests.get(url)
        return res.json()

class WeedVolume:
    def __init__(self, host='127.0.0.1', port=38080):
        self.host = host
        self.port = port

    def upload(self, fid, file_bytes, name='default'):
        '''
        upload file by binary array
        :param fid:
        :param file_bytes:
        :param name:
        :return:
        '''
        url = 'http://' + self.host + ':' + str(self.port) + '/' + fid
        res = requests.put(url, files={name:file_bytes})
        return res.json()

    def dowload(self, fid):
        '''
        download file to binary array
        :param fid:
        :return:
        '''
        url = 'http://' + self.host + ':' + str(self.port) + '/' + fid
        res = requests.get(url)
        return res.content

if __name__ == '__main__':
    weed = WeedMaster('192.168.1.6', 9333)
    #weed.assign()
    #weed.lookup("17,03eb52d0de")
    #weed.status()

    weed2 = WeedVolume('192.168.1.6', 38080)
    # with open('F:\\man.jpg', 'rb') as f:
    #     bs = f.read()
    # ret = weed.assign()
    # print(ret['fid'])
    # ret = weed2.upload(ret['fid'], bs, 'man.jpg')
    # print(ret)

    # ret_bytes = weed2.dowload('1,08bc086fdd')
    # with open('F:\\hhh.jpg', 'wb') as f:
    #     f.write(ret_bytes)

