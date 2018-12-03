CREATE TABLE IF NOT EXISTS `t_camera`(
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `name` VARCHAR(100) DEFAULT 'Default Camera' COMMENT '摄像头名称',
  `url` VARCHAR(100) NOT NULL COMMENT '摄像头RTSP地址',
  `rate` INT DEFAULT 1 COMMENT '抓帧频率',
  `grab` INT DEFAULT 1 COMMENT '0表示不开启抓图，1表示开启抓图',
  `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` timestamp NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
)