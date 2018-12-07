import pymysql

class Mysql():
    def __init__(self, host, port, user, password, db, charset='utf-8'):
        '''
        数据库连接初始化
        :param host:
        :param port:
        :param user:
        :param password:
        :param db:
        :param charset:
        '''
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db
        self.charset = charset
        self.__create_connection()

    def set_logger(self, logger):
        self.logger = logger

    def __create_connection(self):
        self.connection = pymysql.connect(host=self.host, port=self.port, user=self.user,
                               password=self.password, db=self.db, charset=self.charset)

    def insert(self, sql, args=None):
        '''
        插入操作，返回对象自动生成的ID
        :param sql:
        :param args:
        :return:
        '''
        cursor = self.connection.cursor()
        try:
            ret = cursor.execute(sql, args)
            if hasattr(self, 'logger'):
                self.logger.info('SQL execute success! %d row has been changed!' % ret)
            #self.connection.commit()
            id = self.connection.insert_id()
            cursor.close()
            return id
        except pymysql.MySQLError:
            if hasattr(self, 'logger'):
                self.logger.error('MySQL error! roll back ...')
            self.rollback()
            cursor.close()
            return -1

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


    def delete(self, sql, args=None):
        '''
         删除操作
         :param sql:
         :param args:
         :return: no
         '''
        self.update(sql, args)

    def update(self, sql, args=None):
        '''
        更新操作, 需要手动commit
        :param sql:
        :param args:
        :return: no
        '''
        cursor = self.connection.cursor()
        try:
            ret = cursor.execute(sql, args)
            if hasattr(self, 'logger'):
                self.logger.info('SQL execute success! %d row has been changed!' % ret)
            #self.connection.commit()
            cursor.close()
            return True
        except pymysql.MySQLError:
            if hasattr(self, 'logger'):
                self.logger.error('MySQL error! roll back ...')
            self.rollback()
            cursor.close()
            return False

    def select(self, sql, args=None):
        '''
        查询操作, 返回要查询的结果
        :param sql:
        :param args:
        :return: 查询结果, 返回一个二维list
        '''
        cursor = self.connection.cursor()
        try:
            ret = cursor.execute(sql, args)
            if hasattr(self, 'logger'):
                self.logger.info('SQL execute success! %d row has been changed!' % ret)
            data = cursor.fetchall()
            self.commit()
            cursor.close()
            return data
        except pymysql.MySQLError:
            if hasattr(self, 'logger'):
                self.logger.error('MySQL error! roll back ...')
            self.rollback()
            cursor.close()
            return [[]]

    def truncate(self, table_name):
        sql = 'truncate t_camera'
        cursor = self.connection.cursor()
        try:
            ret = cursor.execute(sql)
            if hasattr(self, 'logger'):
                self.logger.info('SQL execute success! %s has been truncated!' % table_name)
            self.commit()
            cursor.close()
        except pymysql.MySQLError:
            if hasattr(self, 'logger'):
                self.logger.error('MySQL error! roll back ...')
            self.rollback()
            cursor.close()
