#!/usr/bin/env bash

cwd=$PWD

read -p 'Enter the IP Address of the Primary OSP Node:' ipaddress

# Get Dependancies
sudo apt-get update
sudo apt-get install build-essential libpcre3 libpcre3-dev libssl-dev unzip git -y

# Build Nginx with RTMP module
if cd /tmp
then
        sudo wget "http://nginx.org/download/nginx-1.17.3.tar.gz"
        sudo wget "https://github.com/arut/nginx-rtmp-module/archive/v1.2.1.zip"
        sudo wget "http://www.zlib.net/zlib-1.2.11.tar.gz"
        sudo tar xvfz nginx-1.17.3.tar.gz
        sudo unzip v1.2.1.zip
        sudo tar xvfz zlib-1.2.11.tar.gz
        if cd nginx-1.17.3
        then
                ./configure --with-http_ssl_module --with-http_v2_module --with-http_auth_request_module --add-module=../nginx-rtmp-module-1.2.1 --with-zlib=../zlib-1.2.11 --with-cc-opt="-Wimplicit-fallthrough=0"
                sudo make install
        else
                echo "Unable to Build Nginx! Aborting."
                exit 1
        fi
else
        echo "Unable to Download Nginx due to missing /tmp! Aborting."
        exit 1
fi

cd $cwd

# Grab Configuration
sudo cp *.conf /usr/local/nginx/conf/

# Setup Configuration with IP
sed -i "s/CHANGEME/$ipaddress/g" /usr/local/nginx/conf/osp-rtmp.conf
sed -i "s/CHANGEME/$ipaddress/g" /usr/local/nginx/conf/nginx.conf

# Enable SystemD

sudo cp nginx-osp.service /etc/systemd/system/osp-edge.service
sudo systemctl daemon-reload
sudo systemctl enable osp-edge.service

# Create HLS directory
sudo mkdir -p /var/www
sudo mkdir -p /var/www/live
sudo mkdir -p /var/www/live-adapt

sudo chown -R www-data:www-data /var/www

#Setup FFMPEG for recordings and Thumbnails
sudo add-apt-repository ppa:jonathonf/ffmpeg-4 -y
sudo apt-get update
sudo apt-get install ffmpeg -y

# Start Nginx
sudo systemctl start osp-edge.service