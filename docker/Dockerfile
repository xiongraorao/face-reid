FROM harbor.oceanai.com.cn/library/face-reid:base

MAINTAINER <xiongraorao@gmail.com>

RUN apt install -y vim

RUN git clone https://github.com/xiongraorao/face-reid.git -b docker

WORKDIR $HOME/face-reid

RUN mkdir linux-build-cmake-make && cp ../ffmpeg-python/linux-build-cmake-make/ffmpeg-python.so ./linux-build-cmake-make/

VOLUME ["$HOME/face-reid/logs/"]

EXPOSE 5000

ENTRYPOINT ["/bin/bash", "-c", "python $CMD"]