FROM python:3.6.8-slim-stretch

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN pip install Flask==1.0.2 \
    && pip install kafka-python==1.4.4 \
    && pip install numpy==1.15.4 \
    && pip install requests==2.20.0 \
    && pip install opencv-python==3.4.3.18 \
    && pip install opencv-contrib-python==3.4.5.20 \
    && pip install PyMySQL==0.9.2 \
    && pip install pyzmq==17.1.2 \
    && pip install schedule==0.5.0 \
    && pip install scikit-learn==0.20.0

COPY sources.list /etc/apt/sources.list

RUN apt-get update && apt-get install -y git && apt-get install -y libgtk2.0-dev

ENV HOME=/home/app

WORKDIR $HOME

# 编译库

RUN git clone http://gitlab.oceanai.com.cn/truthbean/ffmpeg-python.git \
    && cd ffmpeg-python && apt install -y cmake make nasm clang && bash build.sh

RUN rm -rf ffmpeg-python/src ffmpeg-python/CMakeLists.txt