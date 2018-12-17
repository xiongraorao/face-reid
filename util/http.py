import base64

import requests


def get_as_base64(url):
    '''
    获取URL的二进制数据的base64编码
    :return:
    '''
    res = requests.get(url)
    b = res.content
    return base64.b64encode(b).decode('utf-8')