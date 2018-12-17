GLOBAL_ERR = {
    'json_syntax_err': 'JSON syntax error',
    'param_err': 'parameters is illegal'
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

TRACE_ERR = {
    'time_format_err': 'start or end time format error, eg: 2018-01-01 01:01:01',
    'success': 'get trace success'
}

FREQ_ERR = {
    'time_format_err': 'start or end time format error, eg: 2018-01-01 01:01:01',
    'success' : 'get frequency success'
}

REPO_ERR = {
    'success': 'repository operation succeeded',
    'fail': 'repository operation failed'
}