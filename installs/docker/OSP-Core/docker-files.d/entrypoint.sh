#!/usr/bin/env bash
echo 'Placing Configuration Files'
cp -u -p /opt/osp/installs/nginx-core/nginx.conf /usr/local/nginx/conf/
cp -u -p /opt/osp/installs/nginx-core/mime.types /usr/local/nginx/conf/
cp -u -p /opt/osp/setup/nginx/locations/* /usr/local/nginx/conf/locations
cp -u -p /opt/osp/setup/nginx/upstream/* /usr/local/nginx/conf/upstream

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
  chown -R www-data:www-data /var/log/gunicorn
echo 'Setting up OSP Configuration'

chown -R www-data:www-data /opt/osp/conf/config.py
echo 'Performing DB Migrations'
cd /opt/osp

if [[ ! -d /opt/osp/migrations ]]; then
    python3 manage.py db init
fi
python3 manage.py db migrate
python3 manage.py db upgrade
cd /

echo 'Fixing OSP Permissions Post Migration'
chown -R www-data:www-data /opt/osp

echo 'Starting OSP'
supervisord --nodaemon --configuration /opt/osp/setup/supervisord.conf
