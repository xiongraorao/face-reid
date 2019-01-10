FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install apache2 php php-mysql unzip -yqq && apt-get clean

WORKDIR /var/www/html

COPY htdocs.zip ./

RUN unzip -o htdocs.zip -d ./ && chown -R www-data:www-data htdocs/ && mv htdocs/* ./ && rm -rf htdocs.zip htdocs/

CMD ["/usr/sbin/apache2ctl", "-D", "FOREGROUND"]