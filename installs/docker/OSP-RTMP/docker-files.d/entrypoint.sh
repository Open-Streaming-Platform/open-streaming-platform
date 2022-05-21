#!/usr/bin/env bash
echo 'Placing Configuration Files'
cp -u /repo/flask-nginx-rtmp-manager/installs/osp-rtmp/setup/nginx/servers/* /usr/local/nginx/conf/servers
cp -p /repo/flask-nginx-rtmp-manager/installs/osp-rtmp/setup/nginx/services/* /usr/local/nginx/conf/services

echo 'Setting up Directories'
  mkdir -p /var/www && \
  mkdir -p /var/www/live && \
  mkdir -p /var/www/videos && \
  mkdir -p /var/www/live-adapt && \
  mkdir -p /var/www/stream-thumb && \
  mkdir -p /var/www/images  && \
  mkdir -p /var/www/keys && \
  mkdir -p /var/www/keys-adapt && \
  mkdir -p /var/www/pending && \
  mkdir -p /var/www/ingest && \
  mkdir -p /var/log/gunicorn && \
  mkdir -p /var/log/osp && \
  chown -R www-data:www-data /var/www && \
  chown -R www-data:www-data /var/log/gunicorn && \
  chown -R www-data:www-data /var/log/osp
echo 'Setting up OSP Configuration'

export OSP_API_HOST
export OSP_RTMP_SECRETKEY
export OSP_RTMP_DEBUG

echo 'Fixing OSP Permissions Post Migration'
chown -R www-data:www-data /opt/osp-rtmp

echo 'Starting OSP'
supervisord --nodaemon --configuration /opt/osp-rtmp/docker-files.d/supervisord.conf
