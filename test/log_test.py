from util.logger import Log
from cluster.measure import Sample
import logging

if __name__ == '__main__':
    logger = Log('test2', level=logging.DEBUG)
    logger.info('this is info msg')
    logger.debug('this is debug msg')
    logger.error('this is error msg')
    logger.warning('this is warning msg')
