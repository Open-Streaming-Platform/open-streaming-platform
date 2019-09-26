FROM alpine:latest
MAINTAINER David Lockwood

ARG NGINX_VERSION=1.17.3
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
  linux-headers \
  zlib-dev

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
  --with-http_v2_module \
  --with-cc-opt="-Wimplicit-fallthrough=0" \
  --add-module=../nginx-rtmp-module-${NGINX_RTMP_VERSION} && \
  cd /tmp/nginx-${NGINX_VERSION} && make && make install

# Configure NGINX
RUN cp /opt/osp/setup/nginx/*.conf /usr/local/nginx/conf/
RUN cp /opt/osp/setup/nginx/mime.types /usr/local/nginx/conf/

# Install Python, Gunicorn, and uWSGI
RUN apk add python3 \
  py3-setuptools \
  python3-dev \
  py3-gunicorn \
  uwsgi-python3

# Install OSP Dependancies
RUN pip3 install -r /opt/osp/setup/requirements.txt

# Upgrade PIP
RUN pip3 install --upgrade pip

# Setup FFMPEG for recordings and Thumbnails
RUN apk add ffmpeg

# Install Supervisor
RUN apk add supervisor
RUN mkdir -p /var/log/supervisor

RUN cd /opt/osp && python3 manage.py db init

VOLUME ["/var/www", "/usr/local/nginx/conf", "/opt/osp/db", "/opt/osp/conf"]

RUN chmod +x /opt/osp/setup/docker/entrypoint.sh
ENTRYPOINT ["/opt/osp/setup/docker/entrypoint.sh"]
