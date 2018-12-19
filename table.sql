# 摄像头表
CREATE TABLE IF NOT EXISTS `t_camera`(
  `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '摄像头ID',
  `name` VARCHAR(100) DEFAULT 'Default Camera' COMMENT '摄像头名称',
  `url` VARCHAR(100) NOT NULL COMMENT '摄像头RTSP地址',
  `rate` INT DEFAULT 1 COMMENT '抓帧频率',
  `grab` INT DEFAULT 1 COMMENT '0表示不开启抓图，1表示开启抓图',
  `state` INT DEFAULT 1 COMMENT '摄像头状态',
  `create_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
);


# 动态库分类结果
CREATE TABLE IF NOT EXISTS `t_cluster`(
  `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '人脸特征的索引ID, 样本ID',
  `cluster_id` INT NOT NULL COMMENT '动态库聚类的ID',
  `uri` VARCHAR(100) NOT NULL COMMENT '抓拍人员的URI',
  `timestamp` TIMESTAMP NOT NULL COMMENT '抓拍时间',
  `camera_id` INT NOT NULL COMMENT '抓拍摄像头的ID'
);
CREATE INDEX cluster ON `t_cluster`(cluster_id); # 给动态库的cluster创建索引, 用于轨迹查询


# 静态库表
CREATE TABLE IF NOT EXISTS `t_lib`(
  `repository_id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '人像库ID',
  `name` VARCHAR(100) NOT NULL COMMENT '人像库名称'
);

# 静态库成员表
CREATE TABLE IF NOT EXISTS `t_person`(
  `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT 'person_id',
  `name` VARCHAR(100) NOT NULL COMMENT '人员名字，传入数据的person_id',
  `uri` VARCHAR(100) NOT NULL COMMENT '人员图片路径',
  `repository_id` INT NOT NULL COMMENT '人像库ID',
  FOREIGN KEY (`repository_id`)REFERENCES `t_lib`(`repository_id`)
    ON UPDATE CASCADE ON DELETE CASCADE
);


# 动态cluster 和 静态库的关联
CREATE TABLE IF NOT EXISTS `t_contact`(
  `id` INT PRIMARY KEY COMMENT 'person_id，用于和动态库关联',
  `cluster_id` VARCHAR(100) NOT NULL COMMENT '动态库的类ID',
  `similarity` FLOAT COMMENT '该person和cluster_id的相似度',
  FOREIGN KEY (id) REFERENCES `t_person`(`id`) ON UPDATE CASCADE ON DELETE CASCADE
);

# search 查询结果
CREATE TABLE IF NOT EXISTS `t_search`(
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `cluster_id` VARCHAR(100) COMMENT '待查对象所属的类ID',
  `similarity` FLOAT COMMENT '相似度',
  `query_id` INT COMMENT 'query_id, 用于找到结果'
);

# trace 轨迹查询结果，速度够快的话，可以不用存结果到数据库
CREATE TABLE IF NOT EXISTS `t_trace`(
  `query_id` INT PRIMARY KEY AUTO_INCREMENT COMMENT 'query task id',
  `total` INT DEFAULT 0 COMMENT 'total result count',
  `sample_id` INT COMMENT '某个抓拍的人的ID',
  FOREIGN KEY (`sample_id`) REFERENCES `t_cluster`(`id`) ON UPDATE CASCADE ON DELETE CASCADE
);

# freq 频次查询结果，速度够快的话，可以不用存结果到数据库
CREATE TABLE IF NOT EXISTS `t_freq`(
  `query_id` INT PRIMARY KEY AUTO_INCREMENT COMMENT 'query task id',
  `total` INT DEFAULT 0 COMMENT 'total result count',
  `sample_id` INT COMMENT '某个抓拍的人的ID',
  FOREIGN KEY (`sample_id`) REFERENCES `t_cluster`(`id`) ON UPDATE CASCADE ON DELETE CASCADE
);

# 同行人
CREATE TABLE IF NOT EXISTS `t_peer`(
  `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '标识查询结果',
  `query_id` INT COMMENT 'query_id, 用于查找结果',
  `total` INT DEFAULT 0 COMMENT 'total result count',
  `cluster_id` INT COMMENT '和目标同行的cluster_id',
  `times` INT COMMENT '目标人员和该cluster人员的同行次数',
  `start_time` TIMESTAMP COMMENT '开始同行时间',
  `end_time` TIMESTAMP COMMENT '结束同行时间',
  `prob` VARCHAR(10) COMMENT '两个人同行的概率'
);

CREATE TABLE IF NOT EXISTS `t_peer_detail`(
  `id` INT COMMENT '对应t_peer 表的id，用于存储具体的detail信息',
  `src_img` varchar(100) COMMENT '同行的某时刻的目标抓拍照',
  `peer_img` varchar(100) COMMENT '同行的某时刻的同行人抓拍照',
  `src_time` TIMESTAMP COMMENT '同行的某时刻的目标抓拍时间',
  `peer_time` TIMESTAMP COMMENT '同行的某时刻的同行人抓拍时间',
  `camera_id` INT COMMENT '在具体的哪一个摄像机下同行'
);

# 设置SQL mode

# 查看当前模式：
SELECT @@GLOBAL.sql_mode;
SELECT @@SESSION.sql_mode;
SELECT @@sql_mode;
# doc: https://blog.csdn.net/kk185800961/article/details/79426041