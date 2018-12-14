GLOBAL_ERR = {
    'json_syntax_err': 'JSON syntax error',
    'param_err': 'parameters is illegal'
}

CAM_ERR = {
    'success': 'camera operation succeeded',
    'fail': 'camera operation failed'
}

SEARCH_ERR = {
    'start': 'search process has started',
    'success': 'search operation succeeded',
    'fail': 'search operation failed',
    'query_not_exist': 'query task id is not exist',
    'query_in_progress': 'query task is in progress',
    'null': 'search result is null'
}

CAM_INIT_ERR = {
    -1: 'network init error',
    -2: 'could not open url',
    -3: 'has no video stream',
    -4: 'find video stream error',
    -5: 'find decoder error',
    -6: 'parse codec error',
    -7: 'malloc stream context error',
    -8: 'copy codec params error',
    -9: 'open codec error',
    -10: 'find video frame error'
}

CAM_GRAB_ERR = {
    -1: 'malloc frame error',
    -2: 'malloc packet error',
    -3: 'has no video stream',
    -4: 'decode packet error',
    -5: 'decode frame error',
    -6: 'data is null, network may be error',
    -10: 'malloc new frame error',
    -20: 'malloc new frame error',
    -30: 'not init error'
}
