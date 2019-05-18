pip3 install -r /opt/osp/setup/requirements.txt
cp /usr/local/nginx/conf/nginx.conf /usr/local/nginx/conf/nginx.conf.old
cp /opt/osp/setup/nginx/nginx.conf /usr/local/nginx/conf/nginx.conf

sudo mkdir /var/www/live-adapt
sudo chown -R www-data:www-data /var/www/live-adapt
sudo mkdir /var/www/stream-thumb
sudo chown -R www-data:www-data /var/www/stream-thumb