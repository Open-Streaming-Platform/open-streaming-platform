FROM ubuntu:22.04
MAINTAINER David Lockwood

ARG OSP_VERSION=0.9.0
ARG OSP_GIT_BRANCH=build/0.9.x

ARG NGINX_VERSION=1.22.0
ARG NGINX_RTMP_VERSION=1.2.10
ARG NGINX_ZLIB_VERSION=1.2.13

ARG DEFAULT_API=http://127.0.0.1:5010
ARG DEFAULT_FLASK_SECRET=CHANGEME
ARG DEFAULT_DEBUG=false

ARG DEFAULT_TZ="ETC/UTC"

ENV OSP_API_HOST=$DEFAULT_API
ENV OSP_RTMP_SECRETKEY=$DEFAULT_FLASK_SECRET
ENV OSP_RTMP_DEBUG=$DEFAULT_DEBUG
ENV OSP_RTMP_OME

EXPOSE 1935/tcp

# Get initial dependancies
RUN apt update
RUN apt install -y wget build-essential libpcre3 libpcre3-dev libssl-dev unzip libpq-dev curl git

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -y install tzdata

ENV TZ=$DEFAULT_TZ

RUN apt install -y bash

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
#RUN cp -R /opt/osp-rtmp/installs/osp-rtmp/* /opt/osp-rtmp/

# Transfer OSP Docker Files
#COPY docker-files.d/entrypoint.sh /opt/osp-rtmp
#COPY docker-files.d/supervisord.conf /opt/osp-rtmp

# Create the www-data user
#RUN set -x ; \
#  addgroup -g 82 -S www-data ; \
#  adduser -u 82 -D -S -G www-data www-data && exit 0 ; exit 1

# Set the OSP directory to www-data
RUN chown -R www-data:www-data /opt/osp-rtmp

# Download NGINX
RUN cd /tmp && \
  wget https://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz && \
  tar zxf nginx-${NGINX_VERSION}.tar.gz && \
  rm nginx-${NGINX_VERSION}.tar.gz

# Download the NGINX-RTMP Module
RUN cd /tmp && \
  wget https://github.com/winshining/nginx-http-flv-module/archive/refs/tags/v${NGINX_RTMP_VERSION}.tar.gz && \
  tar zxf v${NGINX_RTMP_VERSION}.tar.gz && rm v${NGINX_RTMP_VERSION}.tar.gz

# Inline Patch NGINX-RTMP
RUN cp /opt/osp-rtmp/installs/nginx-core/patches/mr-1158/1158.patch /tmp/nginx-http-flv-module-${NGINX_RTMP_VERSION}/1158.patch
RUN cd /tmp/nginx-http-flv-module-${NGINX_RTMP_VERSION} && patch -s -p 1 < 1158.patch

RUN cd /tmp && \
  wget "https://bitbucket.org/nginx-goodies/nginx-sticky-module-ng/get/master.tar.gz" && \
  tar xxf master.tar.gz

RUN cd /tmp && \
    wget -q "http://www.zlib.net/zlib-${NGINX_ZLIB_VERSION}.tar.gz" && \
    tar xfz zlib-${NGINX_ZLIB_VERSION}.tar.gz

# Compile NGINX with the NGINX-RTMP Module
RUN cd /tmp/nginx-${NGINX_VERSION} && \
  ./configure \
  --with-http_ssl_module \
  --with-http_v2_module \
  --with-http_auth_request_module \
  --with-http_stub_status_module \
  --with-cc-opt="-Wimplicit-fallthrough=0" \
  --add-module=../nginx-http-flv-module-${NGINX_RTMP_VERSION} \
  --add-module=../nginx-goodies-nginx-sticky-module-ng-08a395c66e42 \
  --with-zlib=../zlib-${NGINX_ZLIB_VERSION} && \
  cd /tmp/nginx-${NGINX_VERSION} && make && make install

RUN rm -rf /tmp/nginx-${NGINX_VERSION}

# Configure NGINX
RUN mkdir /usr/local/nginx/conf/servers
RUN mkdir /usr/local/nginx/conf/services
RUN mkdir /usr/local/nginx/conf/custom
RUN mkdir /opt/osp-rtmp/rtmpsocket
RUN cp /opt/osp-rtmp/installs/nginx-core/nginx.conf /usr/local/nginx/conf/
RUN cp /opt/osp-rtmp/installs/nginx-core/mime.types /usr/local/nginx/conf/
RUN cp /opt/osp-rtmp/installs/nginx-core/osp-custom-*.conf /usr/local/nginx/conf/custom
RUN cp /opt/osp-rtmp/setup/nginx/custom/* /usr/local/nginx/conf/custom
RUN cp /opt/osp-rtmp/setup/nginx/servers/* /usr/local/nginx/conf/servers
RUN cp /opt/osp-rtmp/setup/nginx/services/* /usr/local/nginx/conf/services
RUN chown -R www-data:www-data /opt/osp-rtmp/rtmpsocket

# Install Python, Gunicorn, and uWSGI
RUN apt install -y python3 python3-pip uwsgi-plugin-python3 python3-dev python3-setuptools

# Upgrade PIP
RUN pip3 install --upgrade pip

# Install OSP Dependancies
RUN pip3 install -r /opt/osp-rtmp/setup/requirements.txt
RUN pip3 install cryptography==3.3.2

# Setup FFMPEG for recordings and Thumbnails
RUN apt install -y ffmpeg

# Add Dialog (used in osp-config.sh)
RUN apt install -y dialog

# Install Supervisor
RUN apt install -y supervisor
RUN mkdir -p /var/log/supervisor

EXPOSE 1935
EXPOSE 9000

VOLUME ["/var/www", "/usr/local/nginx/conf", "/opt/osp-rtmp/conf"]

RUN chmod +x /opt/osp-rtmp/docker-files.d/entrypoint.sh
ENTRYPOINT ["/bin/sh","-c", "/opt/osp-rtmp/docker-files.d/entrypoint.sh"]
