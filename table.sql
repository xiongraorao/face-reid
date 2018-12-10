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

# 动态cluster 和 静态库的关联
CREATE TABLE IF NOT EXISTS `t_contact`(
  `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '人员ID，用于和动态库关联',
  `cluster_id` VARCHAR(100) NOT NULL COMMENT '动态库的类ID',
  `repository_id` INT COMMENT '人像库ID',
  `person_id` VARCHAR(100) COMMENT '人员ID',
  FOREIGN KEY (id) REFERENCES `t_person`(`id`) ON UPDATE CASCADE ON DELETE CASCADE,
  FOREIGN KEY (repository_id) REFERENCES `t_lib`(`repository_id`) ON UPDATE CASCADE ON DELETE CASCADE
);

# 静态库表
CREATE TABLE IF NOT EXISTS `t_lib`(
  `repository_id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '人像库ID',
  `name` VARCHAR(100) NOT NULL COMMENT '人像库名称'
);

# 静态库成员表
CREATE TABLE IF NOT EXISTS `t_person`(
  `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '用于和动态库关联',
  `person_id` VARCHAR(100) NOT NULL COMMENT '人员ID(名字)',
  `uri` VARCHAR(100) NOT NULL COMMENT '人员图片路径',
  `repository_id` INT NOT NULL COMMENT '人像库ID',
  FOREIGN KEY (`repository_id`)REFERENCES `t_lib`(`repository_id`)
    ON UPDATE CASCADE ON DELETE CASCADE
);

# search 查询结果
CREATE TABLE IF NOT EXISTS `t_search`(
  `query_id` INT PRIMARY KEY AUTO_INCREMENT COMMENT 'query task id',
  `total` INT COMMENT 'total result count',
  `cluster_id` VARCHAR(100) COMMENT '待查对象所属的类ID',
  `face_image_uri` VARCHAR(100) COMMENT '类锚点人脸图的URI',
  `similarity` FLOAT COMMENT '相似度'
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
  `query_id` INT PRIMARY KEY AUTO_INCREMENT COMMENT 'query task id',
  `total` INT DEFAULT 0 COMMENT 'total result count',
  `cluster_id` INT COMMENT '和目标同行的cluster_id',
  `prob` VARCHAR(10) COMMENT '两个人同行的概率',
  `src_img` VARCHAR(100) COMMENT '目标人图片的URL',
  `sample_id` INT COMMENT '同行人的ID（sample_id)'
);

# test
CREATE TABLE `t_test`(
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `time` DATETIME
)