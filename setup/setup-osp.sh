#!/usr/bin/env bash

cwd=$PWD

# Get Dependancies
sudo apt-get install build-essential libpcre3 libpcre3-dev libssl-dev unzip -y

# Setup Python
sudo apt-get install python3.7 python3-pip gunicorn3 uwsgi-plugin-python -y
sudo pip3 install -r requirements.txt
cd ..
cd ..
sudo cp -R flask-nginx-rtmp-manager /opt/osp


# Build Nginx with RTMP module
cd /tmp
sudo wget "http://nginx.org/download/nginx-1.13.10.tar.gz"
sudo wget "https://github.com/arut/nginx-rtmp-module/archive/master.zip"
tar xvfz nginx-1.13.10.tar.gz
unzip master.zip
cd nginx-1.13.10
./configure --with-http_ssl_module --add-module=../nginx-rtmp-module-master
make
sudo make install

# Grab Configuration
cd $cwd/nginx
sudo cp nginx.conf /usr/local/nginx/conf/nginx.conf

# Enable SystemD
cd $cwd/nginx
sudo cp nginx.service /lib/systemd/system/nginx.service
sudo systemctl daemon-reload
sudo systemctl enable nginx.service

cd $cwd/gunicorn
sudo cp osp.service /lib/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable osp.service

# Create HLS directory
cd /var/
sudo mkdir www
sudo chown -R www-data:www-data www
cd www
sudo mkdir live
sudo chown -R www-data:www-data live
sudo mkdir videos
sudo chown -R www-data:www-data videos
sudo mkdir live-rec
sudo chown -R www-data:www-data live-rec
sudo mkdir images
sudo chown -R www-data:www-data images

sudo chown -R www-data:www-data /opt/osp

#Setup FFMPEG for recordings and Thumbnails
sudo apt-get install ffmpeg -y

# Start Nginxcd o
sudo systemctl start nginx.service
sudo systemctl start osp

