FROM alpine:latest
MAINTAINER David Lockwood

ARG NGINX_VERSION=1.15.3
ARG NGINX_RTMP_VERSION=1.2.1

EXPOSE 80/tcp
EXPOSE 443/tcp
EXPOSE 1935/tcp


# Get initial dependancies
RUN apk update
RUN apk add alpine-sdk \
  pcre-dev \
  libressl2.7-libcrypto \
  openssl-dev \
  wget \
  git \
  linux-headers

RUN apk add --no-cache bash

# Make OSP Install Directory
COPY . /opt/osp/

# Create the www-data user
RUN set -x ; \
  addgroup -g 82 -S www-data ; \
  adduser -u 82 -D -S -G www-data www-data && exit 0 ; exit 1

# Set the OSP directory to www-data
RUN chown -R www-data:www-data /opt/osp

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
  --add-module=../nginx-rtmp-module-${NGINX_RTMP_VERSION} && \
  cd /tmp/nginx-${NGINX_VERSION} && make && make install


# Configure NGINX
RUN cp /opt/osp/setup/nginx/nginx.conf /usr/local/nginx/conf/nginx.conf

# Establish the Video and Image Directories
RUN mkdir /var/www && \
  mkdir /var/www/live && \
  mkdir /var/www/videos && \
  mkdir /var/www/live-rec && \
  mkdir /var/www/images  && \
  mkdir /var/log/gunicorn && \
  chown -R www-data:www-data /var/www && \
  chown -R www-data:www-data /var/log/gunicorn

# Install Python, Gunicorn, and uWSGI
RUN apk add python2 \
  py-pip \
  python2-dev \
  py-gunicorn \
  uwsgi-python

# Install OSP Dependancies
RUN pip install -r /opt/osp/setup/requirements.txt

# Upgrade PIP
RUN pip install --upgrade pip

# Setup FFMPEG for recordings and Thumbnails
RUN apk add ffmpeg

# Copy the Default Config File
RUN cp /opt/osp/conf/config.py.dist /opt/osp/conf/config.py

# Install Supervisor
RUN apk add supervisor
RUN mkdir -p /var/log/supervisor

VOLUME ["/var/www", "/usr/local/nginx/conf", "/opt/osp/db", "/opt/osp/conf"]

CMD supervisord --nodaemon --configuration /opt/osp/setup/supervisord.conf
