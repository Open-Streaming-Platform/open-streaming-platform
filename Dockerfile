FROM ubuntu:16.04
MAINTAINER David Lockwood

ARG NGINX_VERSION=1.15.3
ARG NGINX_RTMP_VERSION=1.2.1
ARG cwd=$PWD

EXPOSE 80/tcp
EXPOSE 443/tcp
EXPOSE 1935/tcp

# Get initial dependancies
RUN apt-get update
RUN apt-get install -y \
  build-essential \
  libpcre3 \
  libpcre3-dev \
  libssl-dev \
  unzip \
  wget

# Download NGINX
RUN cd /tmp && \
  wget https://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz && \
  tar zxf nginx-${NGINX_VERSION}.tar.gz && \
  rm nginx-${NGINX_VERSION}.tar.gz

# Download the NGINX-RTMP Module
RUN cd /tmp && \
  wget https://github.com/arut/nginx-rtmp-module/archive/v${NGINX_RTMP_VERSION}.tar.gz && \
  tar zxf v${NGINX_RTMP_VERSION}.tar.gz && rm v${NGINX_RTMP_VERSION}.tar.gz

# Compile NGINX with the NGINX-RTMP Module
RUN cd /tmp/nginx-${NGINX_VERSION} && \
  ./configure \
  --with-http_ssl_module \
  --add-module=../nginx-rtmp-module-master && \
  cd /tmp/nginx-${NGINX_VERSION} && make && make install

# Configure NGINX and SystemD
COPY $cwd/nginx/nginx.conf /usr/local/nginx/conf/nginx.conf
COPY $cwd/nginx/nginx.service /lib/systemd/system/nginx.service
RUN systemctl daemon-reload && enable nginx.service

# Establish the Video and Image Directories
RUN mkdir /var/www && \
  mkdir /var/www/live && \
  mkdir /var/www/videos && \
  mkdir /var/www/live-rec && \
  mkdir /var/www/images  && \
  chown -R www-data:www-data /var/www

# Install Python, Gunicorn, and uWSGI
RUN apt-get install -y \
  python2.7 \
  python-pip \
  gunicorn \
  uwsgi-plugin-python

# Install OSP Dependancies
RUN pip install \
  flask \
  flask-sqlalchemy \
  flask-security \
  flask-socketio \
  gevent \
  flask-uploads \
  psutil \
  requests

# Install Flask-Security Fix
RUN pip install --upgrade git+ https://github.com/mattupstate/flask-security.git@develop

# Make OSP Install Directory
COPY $cwd/flask-nginx-rtmp-mgmt/ /opt/osp/
RUN chown -R www-data:www-data /opt/osp

# Setup FFMPEG for recordings and Thumbnails
RUN apt-get install ffmpeg -y

# Copy the Default Config File
RUN cp /opt/osp/config.py.dist /opt/osp/config.py

VOLUME /www
VOLUME /usr/local/nginx/conf/
VOLUME /opt/osp/config.py
VOLUME /opt/osp/database.db

# Start Nginx
RUN systemctl start nginx.service && systemctl start osp