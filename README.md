# Face-ReID

人脸身份重识别

# 使用步骤

``` bash
git clone https://github.com/xiongraorao/face-reid.git
cd face-reid
pip install -r requirements.txt
python demo.py
python visualize.py
```

# API 文档

[API文档](doc/api.md)

# 简介

## 同行人计算方法

1、根据给定的限制条件，找到目标cluster在t时刻出现在c摄像头的元组列表，记为：

$$ \{(t_1, c_1), (t_2, c_2), ..., (t_m, c_m)\} $$

$ (t_k, c_k) ( 1<= k <= m ) $ 表示的是 目标cluster在`t_k`时刻在`c_k`摄像头下被抓拍到

2、根据给定的时间间隔参数，依次统计目标cluster在`t_k`时刻前后gap时间段内，在`c_k`摄像头中出现的cluster的集合$ D_k $，统计 m 个 $ D_k $中cluster出现的次数和m的比值超过一定概率的cluster，并输出，作为同行人的cluster出现

