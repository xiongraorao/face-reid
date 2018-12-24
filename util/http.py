import base64

import requests


def get_as_base64(url):
    '''
    获取URL的二进制数据的base64编码
    :return:
    '''
    try:
        res = requests.get(url, timeout=3)
        if res.status_code != 200:
            return None
    except (requests.exceptions.RequestException, requests.exceptions.ConnectTimeout) as e:
        print('http request error')
        return None
    b = res.content
    return base64.b64encode(b).decode('utf-8')