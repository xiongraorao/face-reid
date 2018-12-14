<!-- toc -->
- [API 文档](#api-%E6%96%87%E6%A1%A3)
  - [摄像头抓图](#%E6%91%84%E5%83%8F%E5%A4%B4%E6%8A%93%E5%9B%BE)
    - [添加](#%E6%B7%BB%E5%8A%A0)
    - [删除](#%E5%88%A0%E9%99%A4)
    - [修改](#%E4%BF%AE%E6%94%B9)
    - [状态查询](#%E7%8A%B6%E6%80%81%E6%9F%A5%E8%AF%A2)
  - [搜索](#%E6%90%9C%E7%B4%A2)
    - [搜索1](#%E6%90%9C%E7%B4%A21)
    - [搜索2](#%E6%90%9C%E7%B4%A22)
    - [搜索3](#%E6%90%9C%E7%B4%A23)
<!-- toc -->

# API 文档

本文档用于描述该项目实现的若干功能

## 摄像头抓图

该部分主要用来实现摄像头的CURD操作，添加和更新摄像头会根据grab参数来决定是否启动抓图进程

### 添加

请求地址：http://host:port/camera/add
请求方式：post
请求类型：application/json

**输入参数：**

| 参数名 | 是否必选 | 参数类型 | 参数说明
|:---:|:---:|:---:|:---:|
| url | 是 | `string` | 摄像头RTSP地址
| rate | 是 | `int` | 摄像头每秒抓的帧数，默认值1
| grab | 否 | `int` | 是否开启抓图，默认为1，表示采集，0表示不采集
| name | 否 | `string` | 摄像头的名称，便于阅读


**输出参数：**

| 参数名 | 参数类型 | 参数说明
|:---:|:---:|:---:|
| id | `string` | 摄像头id（这里为数据库返回的唯一ID）
| time_used | `int` | 整个请求所花费的时间，单位为毫秒
| rtn | `int` | 请求执行状态；0表示接收正常，非0表示接收异常
| message |	`string` | 请求执行状态描述

### 删除

请求地址：http://host:port/camera/del
请求方式：post
请求类型：application/json

**输入参数：**

| 参数名 | 是否必选 | 参数类型 | 参数说明
|:---:|:---:|:---:|:---:|
| id | 是 | `string` | 摄像头唯一ID


**输出参数：**

| 参数名 | 参数类型 | 参数说明
|:---:|:---:|:---:|
| time_used | `int` | 整个请求所花费的时间，单位为毫秒
| rtn | `int` | 请求执行状态；0表示接收正常，非0表示接收异常
| message |	`string` | 请求执行状态描述


### 修改

请求地址：http://host:port/camera/update
请求方式：post
请求类型：application/json

**输入参数：**

| 参数名 | 是否必选 | 参数类型 | 参数说明
|:---:|:---:|:---:|:---:|
| id | 是 | `string` | 摄像头唯一ID
| url | 是 | `string` | 摄像头RTSP地址
| rate | 是 | `int` | 摄像头每秒抓的帧数，默认值1
| grab | 否 | `int` | 是否开启抓图，默认为1，表示采集，0表示不采集
| name | 否 | `string` | 摄像头的名称，便于阅读


**输出参数：**

| 参数名 | 参数类型 | 参数说明
|:---:|:---:|:---:|
| time_used | `int` | 整个请求所花费的时间，单位为毫秒
| rtn | `int` | 请求执行状态；0表示接收正常，非0表示接收异常
| message |	`string` | 请求执行状态描述

### 状态查询

请求地址：http://host:port/camera/status
请求方式：get
请求类型：application/json

**输入参数：**

| 参数名 | 是否必选 | 参数类型 | 参数说明
|:---:|:---:|:---:|:---:|
| id | 是 | `string` | 摄像头唯一ID

**输出参数：**

| 参数名 | 参数类型 | 参数说明
|:---:|:---:|:---:|
| time_used | `int` | 整个请求所花费的时间，单位为毫秒
| rtn | `int` | 请求执行状态；0表示接收正常，非0表示接收异常
| message |	`string` | 请求执行状态描述
| status | `int` | 1运行中；2已结束，3 无法连接

## 搜索

### 搜索1

功能：给定目标，实现全库检索，返回聚类的id（cluster_id)

请求地址：http://host:port/search/all
请求方式：post
请求类型：application/json

**输入参数：**

| 参数名 | 是否必选 | 参数类型 | 参数说明
|:---:|:---:|:---:|:---:|
| image_base64 | 是	| `string` | 目标图片的Base64编码
| query_id | 否	| `string`  | 结果翻页的时候, 使用这个 id 来查询, 缺省表示重新开启一个任务
| start_pos | 是 | `int` | 从第几个开始返回
| limit | 是 | `int` | 返回至多多少个结果
| camera_ids | 否 | `Array<string>` | 关注的摄像头列表，默认为所有
| topk | 否	| int |	输出多少个检索结果，默认为100（实际上也有可能小于该值）

**输出参数：**

| 参数名 | 参数类型 | 参数说明
|:---:|:---:|:---:|
| time_used | `int` | 整个请求所花费的时间，单位为毫秒
| rtn | `int` | 请求执行状态；0表示接收正常，非0表示接收异常
| message |	`string` | 请求执行状态描述
| total | `int` | 总结果数
| query_id | `string` | 查询请求的id
| results | `Array<object>` | 检索的结果，按照平均相似度的高低来输出
| results.cluster_id | `string` | 目标属于的类别ID
| results.face_image_uri | `string` | 该类的锚点人脸图
| results.similarity | `float` | 目标和该类的所有人脸的平均相似度
| results.repository_infos | `Array<object>` | 关联到的静态库信息
| results.repository_info.person_id | `string` | 人员id
| results.repository_info.repository_id | `string` | 人像库id
| results.repository_info.name | `string` | 人像库名称


### 搜索2

功能：给定静态库，对静态库中的人进行搜索，返回聚类的id（cluster_id)

请求地址：http://host:port/search/repos
请求方式：post
请求类型：application/json

**输入参数：**

| 参数名 | 是否必选 | 参数类型 | 参数说明
|:---:|:---:|:---:|:---:|
| repository_ids | 是 | `Array<string>` | 静态库的ID列表
| query_id | 否	| `string`  | 结果翻页的时候, 使用这个 id 来查询, 缺省表示重新开启一个任务
| start_pos | 是 | `int` | 从第几个开始返回
| limit | 是 | `int` | 返回至多多少个结果
| camera_ids | 否 | `Array<string>` | 关注的摄像头列表，默认为所有
| topk | 否	| int |	输出多少个检索结果，默认为100（实际上也有可能小于该值）

**输出参数：**

| 参数名 | 参数类型 | 参数说明
|:---:|:---:|:---:|
| time_used | `int` | 整个请求所花费的时间，单位为毫秒
| rtn | `int` | 请求执行状态；0表示接收正常，非0表示接收异常
| message |	`string` | 请求执行状态描述
| total | `int` | 总结果数
| query_id | `string` | 查询请求的id
| results | `Array<object>` | 检索的结果，按照平均相似度的高低来输出
| results.cluster_id | `string` | 目标属于的类别ID
| results.face_image_uri | `string` | 该类的锚点人脸图
| results.similarity | `float` | 目标和该类的所有人脸的平均相似度
| results.repository_info | `object` | 关联到的静态库信息
| results.repository_info.person_id | `string` | 人员id
| results.repository_info.repository_id | `string` | 人像库id
| results.repository_info.name | `string` | 人像库名称

### 搜索3

功能：给定目标图片，在静态库中进行搜索，返回聚类的id（cluster_id)

请求地址：http://host:port/search/libs
请求方式：post
请求类型：application/json

**输入参数：**

| 参数名 | 是否必选 | 参数类型 | 参数说明
|:---:|:---:|:---:|:---:|
| image_base64 | 是 | `Array<string>` | 目标图片的Base64编码
| query_id | 否	| `string`  | 结果翻页的时候, 使用这个 id 来查询, 缺省表示重新开启一个任务
| start_pos | 是 | `int` | 从第几个开始返回
| limit | 是 | `int` | 返回至多多少个结果
| camera_ids | 否 | `Array<string>` | 关注的摄像头列表，默认为所有
| topk | 否	| int |	输出多少个检索结果，默认为100（实际上也有可能小于该值）

**输出参数：**

| 参数名 | 参数类型 | 参数说明
|:---:|:---:|:---:|
| time_used | `int` | 整个请求所花费的时间，单位为毫秒
| rtn | `int` | 请求执行状态；0表示接收正常，非0表示接收异常
| message |	`string` | 请求执行状态描述
| total | `int` | 总结果数
| query_id | `string` | 查询请求的id
| results | `Array<object>` | 检索的结果，按照平均相似度的高低来输出
| results.cluster_id | `string` | 目标属于的类别ID
| results.face_image_uri | `string` | 该类的锚点人脸图
| results.similarity | `float` | 目标和该类的所有人脸的平均相似度
| results.repository_info | `object` | 关联到的静态库信息
| results.repository_info.person_id | `string` | 人员id
| results.repository_info.repository_id | `string` | 人像库id
| results.repository_info.name | `string` | 人像库名称
