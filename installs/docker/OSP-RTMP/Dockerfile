FROM ubuntu:20.04
MAINTAINER David Lockwood

ARG OSP_VERSION=0.9.0
ARG OSP_GIT_BRANCH=build/0.9.x

ARG NGINX_VERSION=1.17.3
ARG NGINX_RTMP_VERSION=1.2.1

ARG DEFAULT_API=http://127.0.0.1:5010
ARG DEFAULT_FLASK_SECRET=CHANGEME
ARG DEFAULT_DEBUG=false

ARG DEFAULT_TZ="ETC/UTC"

ENV OSP_API_HOST=$DEFAULT_API
ENV OSP_RTMP_SECRETKEY=$DEFAULT_FLASK_SECRET
ENV OSP_RTMP_DEBUG=$DEFAULT_DEBUG

EXPOSE 1935/tcp

# Get initial dependancies
RUN apk update
RUN apk add alpine-sdk \
  pcre-dev \
  libressl-dev \
  openssl-dev \
  libffi-dev \
  wget \
  git \
  linux-headers \
  zlib-dev \
  postgresql-dev \
  gcc \
  libgcc \
  musl-dev \
  jpeg-dev \
  zlib-dev

RUN apk add --no-cache tzdata

ENV TZ=$DEFAULT_TZ

RUN apk add --no-cache bash

# Download OSP from Repo
#RUN cd /tmp && \
#  wget "https://gitlab.com/Deamos/flask-nginx-rtmp-manager/-/archive/${OSP_VERSION}/flask-nginx-rtmp-manager-${OSP_VERSION}.tar.gz" && \
#  tar zxf flask-nginx-rtmp-manager-${OSP_VERSION}.tar.gz && \
#  rm flask-nginx-rtmp-manager-${OSP_VERSION}.tar.gz

# Clone Branch Instead
#RUN mkdir /repo
#RUN cd /repo && git clone https://gitlab.com/Deamos/flask-nginx-rtmp-manager.git && cd flask-nginx-rtmp-manager && git checkout ${OSP_GIT_BRANCH}

# Build from Local Directory
RUN mkdir -p /opt/osp-rtmp
COPY ./ /opt/osp-rtmp

# Make OSP Install Directory
#RUN mkdir -p /opt/osp-rtmp
#RUN cp -R /repo/flask-nginx-rtmp-manager/installs/osp-rtmp/* /opt/osp-rtmp/

# Transfer OSP Docker Files
#COPY docker-files.d/entrypoint.sh /opt/osp-rtmp
#COPY docker-files.d/supervisord.conf /opt/osp-rtmp

# Create the www-data user
RUN set -x ; \
  addgroup -g 82 -S www-data ; \
  adduser -u 82 -D -S -G www-data www-data && exit 0 ; exit 1

# Set the OSP directory to www-data
RUN chown -R www-data:www-data /opt/osp-rtmp

# Download NGINX
RUN cd /repo && \
  wget https://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz && \
  tar zxf nginx-${NGINX_VERSION}.tar.gz && \
  rm nginx-${NGINX_VERSION}.tar.gz

# Download the NGINX-RTMP Module
RUN cd /repo && \
  wget https://github.com/arut/nginx-rtmp-module/archive/v${NGINX_RTMP_VERSION}.tar.gz && \
  tar zxf v${NGINX_RTMP_VERSION}.tar.gz && rm v${NGINX_RTMP_VERSION}.tar.gz

RUN cd /repo && \
  wget "https://bitbucket.org/nginx-goodies/nginx-sticky-module-ng/get/master.tar.gz" && \
  tar xxf master.tar.gz

RUN cd /tmp && \
    wget -q "http://www.zlib.net/zlib-1.2.12.tar.gz" && \
    tar xfz zlib-1.2.12.tar.gz

# Compile NGINX with the NGINX-RTMP Module
RUN cd /tmp/nginx-${NGINX_VERSION} && \
  ./configure \
  --with-http_ssl_module \
  --with-http_v2_module \
  --with-http_auth_request_module \
  --with-http_stub_status_module \
  --with-cc-opt="-Wimplicit-fallthrough=0" \
  --add-module=../nginx-rtmp-module-${NGINX_RTMP_VERSION} \
  --add-module=../nginx-goodies-nginx-sticky-module-ng-08a395c66e42 \
  --with-zlib=../zlib-1.2.12 && \
  cd /tmp/nginx-${NGINX_VERSION} && make && make install

RUN rm -rf /repo/nginx-${NGINX_VERSION}

# Configure NGINX
RUN mkdir /usr/local/nginx/conf/servers
RUN mkdir /usr/local/nginx/conf/services
RUN mkdir /usr/local/nginx/conf/custom
RUN mkdir /opt/osp-rtmp/rtmpsocket
RUN cp /repo/flask-nginx-rtmp-manager/installs/nginx-core/nginx.conf /usr/local/nginx/conf/
RUN cp /repo/flask-nginx-rtmp-manager/installs/nginx-core/mime.types /usr/local/nginx/conf/
RUN cp /repo/flask-nginx-rtmp-manager/installs/nginx-core/osp-custom-*.conf /usr/local/nginx/conf/custom
RUN cp /repo/flask-nginx-rtmp-manager/installs/osp-rtmp/setup/nginx/custom/* /usr/local/nginx/conf/custom
RUN cp /repo/flask-nginx-rtmp-manager/installs/osp-rtmp/setup/nginx/servers/* /usr/local/nginx/conf/servers
RUN cp /repo/flask-nginx-rtmp-manager/installs/osp-rtmp/setup/nginx/services/* /usr/local/nginx/conf/services
RUN chown -R www-data:www-data /opt/osp-rtmp/rtmpsocket
RUN chown -R www-data:www-data /repo/*

# Install Python, Gunicorn, and uWSGI
RUN apk add python3 \
  py3-pip \
  py3-setuptools \
  python3-dev \
  py3-gunicorn \
  uwsgi-python3

# Upgrade PIP
RUN pip3 install --upgrade pip

# Install OSP Dependancies
RUN pip3 install -r /repo/flask-nginx-rtmp-manager/installs/osp-rtmp/setup/requirements.txt
RUN pip3 install cryptography==3.3.2

# Setup FFMPEG for recordings and Thumbnails
RUN apk add ffmpeg

# Add Dialog (used in osp-config.sh)
RUN apk add dialog

# Install Supervisor
RUN apk add supervisor
RUN mkdir -p /var/log/supervisor

EXPOSE 1935
EXPOSE 9000

VOLUME ["/var/www", "/usr/local/nginx/conf", "/opt/osp-rtmp/conf"]

RUN chmod +x /opt/osp-rtmp/docker-files.d/entrypoint.sh
ENTRYPOINT ["/bin/sh","-c", "/opt/osp-rtmp/docker-files.d/entrypoint.sh"]
