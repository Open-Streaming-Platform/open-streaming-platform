FROM alpine:latest
MAINTAINER David Lockwood

ARG NGINX_VERSION=1.17.3
ARG NGINX_RTMP_VERSION=1.2.1

ARG DEFAULT_DB_URL="sqlite:///db/database.db"
ARG DEFAULT_REDIS_HOST="localhost"
ARG DEFAULT_REDIS_PORT=6379
ARG DEFAULT_REDIS_PASSWORD=NONE
ARG DEFAULT_FLASK_SECRET="CHANGEME"
ARG DEFAULT_FLASK_SALT="CHANGEME"
ARG DEFAULT_OSP_ALLOWREGISTRATION="True"
ARG DEFAULT_OSP_REQUIREVERIFICATION="True"
ARG DEFAULT_TZ="ETC/UTC"

ENV DB_URL=$DEFAULT_DB_URL
ENV REDIS_HOST=$DEFAULT_REDIS_HOST
ENV REDIS_PORT=$DEFAULT_REDIS_PORT
ENV REDIS_PASSWORD=$DEFAULT_REDIS_PASSWORD
ENV FLASK_SECRET=$DEFAULT_FLASK_SECRET
ENV FLASK_SALT=$DEFAULT_FLASK_SALT
ENV OSP_ALLOWREGISTRATION=$DEFAULT_OSP_ALLOWREGISTRATION
ENV OSP_REQUIREVERIFICATION=$DEFAULT_OSP_REQUIREVERIFICATION

EXPOSE 80/tcp
EXPOSE 443/tcp
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

RUN cd /tmp && \
  wget "https://bitbucket.org/nginx-goodies/nginx-sticky-module-ng/get/master.tar.gz" && \
  tar xxf master.tar.gz

# Compile NGINX with the NGINX-RTMP Module
RUN cd /tmp/nginx-${NGINX_VERSION} && \
  ./configure \
  --with-http_ssl_module \
  --with-http_v2_module \
  --with-http_auth_request_module \
  --with-cc-opt="-Wimplicit-fallthrough=0" \
  --add-module=../nginx-rtmp-module-${NGINX_RTMP_VERSION} \
  --add-module=../nginx-goodies-nginx-sticky-module-ng-08a395c66e42 && \
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

# Upgrade PIP
RUN pip3 install --upgrade pip

# Install OSP Dependancies
RUN pip3 install -r /opt/osp/setup/requirements.txt
RUN pip3 install cryptography

# Setup FFMPEG for recordings and Thumbnails
RUN apk add ffmpeg

# Setup Wait-For-It Script
RUN chmod +x /opt/osp/setup/docker/wait-for-it.sh

# Install Supervisor
RUN apk add supervisor
RUN mkdir -p /var/log/supervisor

VOLUME ["/var/www", "/usr/local/nginx/conf", "/opt/osp/db", "/opt/osp/conf"]

RUN chmod +x /opt/osp/setup/docker/entrypoint.sh
ENTRYPOINT ["/bin/sh","-c", "/opt/osp/setup/docker/entrypoint.sh"]
