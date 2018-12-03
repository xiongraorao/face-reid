import configparser,pymysql
output_dir = '/home/xrr/output'
redis_host = '192.168.1.11'
redis_port = 6379
redis_db = 5
ped_db = 7
gpu_id = 1
camera = {
    'cross': 'rtsp://admin:iec123456@192.168.1.72:554/unicast/c1/s0/live',
    'dev': 'rtsp://admin:iec123456@192.168.1.71:554/unicast/c1/s0/live',
    'door': 'rtsp://admin:123456@192.168.1.61:554/h264/ch1/main/av_stream'
}

lfw_dir = '/home/xrr/datasets/lfw-sub'

# search server
search_host = '192.168.1.6'
search_port = 2333


