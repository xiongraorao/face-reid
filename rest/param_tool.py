import re

CAM_RE = {
    'url': r'^/.*$|^/.*$ |^rtsp://.*$',
    'rate': r'^\d$|^1\d$|^2[0-5]$',
    'name': r'^.+$',
    'id': r'^\d+$'
}

G_RE = {
    'datetime': r'^([0-9]{3}[1-9]|[0-9]{2}[1-9][0-9]{1}|[0-9]{1}[1-9][0-9]{2}|[1-9][0-9]{3})-(((0[13578]|1[02])-(0[1-9]|[12][0-9]|3[01]))|((0[469]|11)-(0[1-9]|[12][0-9]|30))|(02-(0[1-9]|[1][0-9]|2[0-8])))'
                r' (0[0-9]:[0-5][0-9]:[0-5][0-9]|1[0-9]:[0-5][0-9]:[0-5][0-9]|2[0-3]:[0-5][0-9]:[0-5][0-9])$',
    'num': r'^\d+$',
    'str': r'^.+$'
}


def check_param_key(input_params, necessary_params, optional_params):
    '''
    参数合法性校验
    :param input_params: 输入参数
    :type   set
    :param necessary_params: 必选参数
    :type set
    :param optional_params: 可选参数
    :type set
    :return:
    '''
    if len(necessary_params - input_params) == 0 \
            and len(input_params - (necessary_params | optional_params)) == 0:
        return True
    return False


def check_param_value(patterns, values):
    '''
    参数合法性校验，检查数据格式
    :param patterns
    :type list[str]
    :param values
    :type list[str]
    :return:
    '''
    if patterns is None or values is None or len(patterns) != len(values):
        return False
    for p, v in zip(patterns, values):
        if re.match(p, str(v)) is None:
            return False
    return True

def update_param(default, input):
    '''
    更新默认参数
    :param default: 默认参数
    :type dict
    :param input: 输入参数
    :type dict
    :return: 更新后的参数
    '''
    ret = default.copy()
    ret.update(input)
    return ret

if __name__ == '__main__':
    input_params = {"url": "rtsp://admin:iec123456@192.168.1.72:554/unicast/c1/s0/live", "rate": 2, "name": "十字路口"}
    nessary_params = {'url'}
    default_params = {'rate': 1, 'grab': 1, 'name': 'Default Camera'}
    result = check_param_key(set(input_params), nessary_params, set(default_params))
    print(result)

    result = check_param_value([CAM_RE['url'], CAM_RE['rate'], CAM_RE['name']],
                               [input_params['url'], input_params['rate'], input_params['name']])
    print(result)
