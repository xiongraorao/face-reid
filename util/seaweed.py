import requests


class WeedClient():
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
        params = {'replication': replication, 'count': count}
        if dataCenter is not None:
            params['dataCenter'] = dataCenter
        res = requests.get(url, params=params)
        return res.json()

    def upload(self, url, fid, file_bytes, name='default'):
        '''
        upload file by binary array
        :param url:
        :param fid:
        :param file_bytes:
        :param name:
        :return:
        '''
        url = 'http://' + url + '/' + fid
        res = requests.put(url, files={name: file_bytes})
        return res.json()

    def download(self, url):
        '''
        download file to binary array
        :param url:
        :return:
        '''
        res = requests.get(url)
        return res.content

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

    def allocate(self, replication='000', count=1, collection=None, dataCenter=None, ttl=None):
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
        res = requests.get(url, params={'collection': collection})
        return res.json()

    def status(self):
        '''
        check status
        :return:
        '''
        url = 'http://' + self.host + ':' + str(self.port) + '/cluster/status'
        res = requests.get(url)
        return res.json()
