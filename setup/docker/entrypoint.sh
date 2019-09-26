#!/usr/bin/env bash
cp -R -u -p /opt/osp/setup/nginx/*.conf /usr/local/nginx/conf/
cp -u -p /opt/osp/setup/nginx/mime.types /usr/local/nginx/conf/
cp -u -p /opt/osp/setup/config.py.dist /opt/osp/conf/config.py
mkdir -p /var/www && \
  mkdir -p /var/www/live && \
  mkdir -p /var/www/videos && \
  mkdir -p /var/www/live-rec && \
  mkdir -p /var/www/live-adapt && \
  mkdir -p /var/www/stream-thumb && \
  mkdir -p /var/www/images  && \
  mkdir -p /var/log/gunicorn && \
  chown -R www-data:www-data /var/www && \
  chown -R www-data:www-data /var/log/gunicorn
chown -R www-data:www-data /opt/osp/conf/config.py

cd /opt/osp
python3 manage.py db migrate
python3 manage.py db upgrade

supervisord --nodaemon --configuration /opt/osp/setup/docker/supervisord.conf
