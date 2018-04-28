#!/usr/bin/env bash

cwd=$PWD

# Get Dependancies
sudo apt-get install build-essential libpcre3 libpcre3-dev libssl-dev unzip -y

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
#cd /tmp
#wget "https://gitlab.com/Deamos/nginx-rtmp-server/raw/master/nginx.conf"
cd $cwd/nginx
sudo cp nginx.conf /usr/local/nginx/conf/nginx.conf

# Enable SystemD
cd $cwd/nginx
sudo cp nginx.service /lib/systemd/system/nginx.service
sudo systemctl daemon-reload
sudo systemctl enable nginx.service

cd $cwd/gunicorn
sudo cp flask-nginx-rtmp-manager.service /lib/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable flask-nginx-rtmp-manager.service


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

# Setup Python
sudo apt-get install python2.7 python-pip gunicorn uwsgi-plugin-python -y
sudo pip install flask flask-sqlalchemy flask-security flask-socketio gevent
sudo mkdir /opt/flask-nginx-rtmp-manager/
cd /opt/flask-nginx-rtmp-manager/
#sudo wget "https://gitlab.com/Deamos/nginx-rtmp-server/raw/master/flask/app.py"
#sudo wget "https://gitlab.com/Deamos/nginx-rtmp-server/raw/master/config.py"

cd $cwd/flask-nginx-rtmp-mgmt
sudo cp -R * /opt/flask-nginx-rtmp-manager

sudo apt-get install ffmpeg -y

# Start Nginx
sudo systemctl start nginx.service
sudo systemctl start flask-nginx-rtmp-manager

