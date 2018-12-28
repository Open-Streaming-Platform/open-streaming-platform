FROM ubuntu:16.04
MAINTAINER David Lockwood

ARG NGINX_VERSION=1.15.3
ARG NGINX_RTMP_VERSION=1.2.1

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
  wget \
  git

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
RUN cd /..
ADD nginx/nginx.conf /usr/local/nginx/conf/nginx.conf

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
ADD requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Upgrade PIP
RUN pip install --upgrade pip

# Make OSP Install Directory
ADD flask-nginx-rtmp-mgmt/ /opt/osp/
RUN chown -R www-data:www-data /opt/osp

# Setup FFMPEG for recordings and Thumbnails
RUN apt-get install ffmpeg -y

# Copy the Default Config File
RUN cp /opt/osp/config.py.dist /opt/osp/config.py

# Install Supervisor
RUN apt-get install -y supervisor
RUN mkdir -p /var/log/supervisor
ADD supervisord.conf /etc/supervisor/conf.d/supervisord.conf

VOLUME ["/var/www","/opt/osp", "/usr/local/nginx/conf"]

CMD ["/usr/bin/supervisord"]
