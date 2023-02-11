#!/usr/bin/env bash
echo 'Placing Configuration Files'
cp -u -p /opt/osp-rtmp/installs/osp-rtmp/setup/nginx/servers/* /usr/local/nginx/conf/servers
cp -u -p /opt/osp-rtmp/installs/osp-rtmp/setup/nginx/services/* /usr/local/nginx/conf/services
cp -u -p /opt/osp-rtmp/installs/osp-rtmp/setup/nginx/custom/osp-rtmp-custom-ome.conf /usr/local/nginx/conf/custom

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
export OSP_RTMP_OME

if [ -n "$OSP_RTMP_OME" ]; then
  echo "push $OSP_RTMP_OME;" > /usr/local/nginx/conf/custom/osp-rtmp-custom-ome.conf
fi


echo 'Fixing OSP Permissions Post Migration'
chown -R www-data:www-data /opt/osp-rtmp

echo 'Starting OSP'
supervisord --nodaemon --configuration /opt/osp-rtmp/docker-files.d/supervisord.conf
