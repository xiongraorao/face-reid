import time
import re

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

def check_param_value(input_values, input_pattern):
    '''
    参数合法性校验，检查数据格式
    :param input_values:
    :type value list
    :param input_pattern:
    :type value list
    :return:
    '''
    if len(input_values) != len(input_pattern):
        return False
    for value,pattern in zip(input_values,input_pattern):
        if not re.match(pattern, value):
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

def check_date(*args):
    for date in args:
        try:
            time.strptime(date, "%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            print(e)
            return False
    return True

if __name__ == '__main__':
    input_params = {"url":"rtsp://admin:iec123456@192.168.1.72:554/unicast/c1/s0/live", "rate":2, "name":"十字路口"}
    nessary_params = {'url'}
    default_params = {'rate': 1, 'grab': 1, 'name': 'Default Camera'}
    result = check_param_key(set(input_params), nessary_params, set(default_params))
    print(result)
    result = check_param_value(list(input_params.values()), [r'rtsp://[.*?]:[.*?]@(^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$):\d+.*'])

