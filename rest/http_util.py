def check_param(input_params, necessary_params, optional_params):
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
            and len(input_params - necessary_params | optional_params) == 0:
        return True
    return False

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