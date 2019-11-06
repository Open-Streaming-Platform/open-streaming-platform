#!/usr/bin/env bash
echo 'Placing Configuration Files'
cp -R -u -p /opt/osp/setup/nginx/*.conf /usr/local/nginx/conf/
cp -u -p /opt/osp/setup/nginx/mime.types /usr/local/nginx/conf/
cp /opt/osp/setup/config.py.dist /opt/osp/conf/config.py
echo 'Setting up Directories'
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
echo 'Setting up OSP Configuration'

export DB_URL
echo "dbLocation='$DB_URL'" > /opt/osp/conf/config.py
export FLASK_SECRET
echo "secretKey='$FLASK_SECRET'" >> /opt/osp/conf/config.py
export FLASK_SALT
echo "passwordSalt='$FLASK_SALT'" >> /opt/osp/conf/config.py
export OSP_ALLOWREGISTRATION
echo "allowRegistration=$OSP_ALLOWREGISTRATION" >> /opt/osp/conf/config.py
export OSP_REQUIREVERIFICATION
echo "requireEmailRegistration=$OSP_REQUIREVERIFICATION" >> /opt/osp/conf/config.py

chown -R www-data:www-data /opt/osp/conf/config.py
echo 'Performing DB Migrations'
cd /opt/osp
python3 manage.py db init
python3 manage.py db migrate
python3 manage.py db upgrade
cd /

echo 'Fixing OSP Permissions Post Migration'
chown -R www-data:www-data /opt/osp

echo 'Starting OSP'
supervisord --nodaemon --configuration /opt/osp/setup/docker/supervisord.conf