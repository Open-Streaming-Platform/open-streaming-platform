#!/usr/bin/env bash
echo 'Placing Configuration Files'
cp -u -p /opt/osp-edge/setup/nginx/locations/* /usr/local/nginx/conf/locations
cp -u -p /opt/osp-edge/setup/nginx/servers/* /usr/local/nginx/conf/servers
cp -u -p /opt/osp-edge/setup/nginx/services/* /usr/local/nginx/conf/services

echo 'Setting up Directories'
  mkdir -p /var/www && \
  mkdir -p /var/www/live && \
  mkdir -p /var/www/live-adapt && \
  mkdir -p /var/log/osp && \
  chown -R www-data:www-data /var/www && \
  chown -R www-data:www-data /var/log/gunicorn
echo 'Setting up OSP Configuration'

export OSPCOREIP
IFS="," read -a coreArray <<< $OSPCOREIP
coreString=""
for i in "${coreArray[@]}"
do
      coreString+="allow $i;\n"
done

export OSPRTMPIP
IFS="," read -a rtmpArray <<< $OSPRTMPIP
rtmpString=""
for i in "${rtmpArray[@]}"
do
      rtmpString+="allow publish $i;\n"
done

sed -i "s/#ALLOWRTMP/$rtmpString/g" /usr/local/nginx/conf/services/osp-edge-rtmp.conf
sed -i "s/#ALLOWCORE/$coreString/g" /usr/local/nginx/conf/servers/osp-edge-servers.conf


echo 'Starting OSP'
supervisord --nodaemon --configuration /opt/osp-edge/supervisord.conf