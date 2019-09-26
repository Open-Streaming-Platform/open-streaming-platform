#!/usr/bin/env bash
cp -R -u -p /opt/osp/setup/nginx/*.conf /usr/local/nginx/conf/
cp -u -p /opt/osp/setup/nginx/mime.types /usr/local/nginx/conf/
cp /opt/osp/setup/config.py.dist /opt/osp/conf/config.py
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

export DB_URL
sed -i 's/dbLocation="sqlite:///db/database.db"/dbLocation="$DB_URL/g' /opt/osp/conf/config.py
export FLASK_SECRET
sed -i 's/secretKey="CHANGEME"/secretKey="$FLASK_SECRET"/g' /opt/osp/conf/config.py
export FLASK_SALT
sed -i 's/passwordSalt="CHANGEME"/passwordSalt="$FLASK_SALT"/g' /opt/osp/conf/config.py
export OSP_ALLOWREGISTRATION
sed -i 's/allowRegistration=True/allowRegistration=$OSP_ALLOWREGISTRATION/g' /opt/osp/conf/config.py
export OSP_REQUIREVERIFICATION
sed -i 's/requireEmailRegistration=True/requireEmailRegistration=$OSP_REQUIREVERIFICATION/g' /opt/osp/conf/config.py

chown -R www-data:www-data /opt/osp/conf/config.py

cd /opt/osp
python3 manage.py db init
python3 manage.py db migrate
python3 manage.py db upgrade

supervisord --nodaemon --configuration /opt/osp/setup/docker/supervisord.conf
