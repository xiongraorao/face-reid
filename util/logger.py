import logging
import os
import sys

LOG_FORMAT = "%(asctime)s (%(name)s) [%(levelname)s] %(message)s"
DATE_FORMAT = "%m/%d/%Y %H:%M:%S"

class Log:
    def __init__(self, name, path='./', is_save = True, level=logging.INFO):
        '''
        initialize logger, default output level is Warning
        :param name: logger programe name
        :param path: logs path to be save
        :param is_save: whether save logs to file
        :param level: file_log level, default DEBUG
        '''
        logging.basicConfig(format=LOG_FORMAT, datefmt=DATE_FORMAT, level=level)
        self.logger = logging.getLogger(name)  # 程序名
        if is_save:
            file_handler = logging.FileHandler(filename=os.path.join(path, name + '.log'), encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            self.logger.addHandler(file_handler)

    def debug(self, msg, *args):
        for arg in args:
            msg += ' ' + str(arg)
        self.logger.debug(msg)

    def info(self, msg, *args):
        for arg in args:
            msg += ' ' + str(arg)
        self.logger.info(msg)

    def warning(self, msg, *args):
        for arg in args:
            msg += ' ' + str(arg)
        self.logger.warning(msg)

    def error(self, msg, *args):
        for arg in args:
            msg += ' ' + str(arg)
        self.logger.error(msg)



