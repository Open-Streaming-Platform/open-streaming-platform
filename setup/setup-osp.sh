#!/usr/bin/env bash

cwd=$PWD

# Get Dependancies
sudo apt-get install build-essential libpcre3 libpcre3-dev libssl-dev unzip git -y

# Setup Python
sudo apt-get install python3 python3-pip uwsgi-plugin-python python3-dev python3-setuptools python3-wheel -y
sudo pip3 install -r requirements.txt

# Install Redis
sudo apt-get install redis -y
sudo sed -i 's/appendfsync everysec/appendfsync no/' /etc/redis/redis.conf
sudo systemctl restart redis

# Setup OSP Directory
mkdir -p /opt/osp
if cd ..
then
        sudo cp -rf -R * /opt/osp
        sudo cp -rf -R .git /opt/osp
else
        echo "Unable to find installer directory. Aborting!"
        exit 1
fi

# Build Nginx with RTMP module
if cd /tmp
then
        sudo wget "http://nginx.org/download/nginx-1.17.3.tar.gz"
        sudo wget "https://github.com/arut/nginx-rtmp-module/archive/v1.2.1.zip"
        sudo wget "http://www.zlib.net/zlib-1.2.11.tar.gz"
        sudo wget "https://bitbucket.org/nginx-goodies/nginx-sticky-module-ng/get/master.tar.gz"
        sudo tar xvfz nginx-1.17.3.tar.gz
        sudo unzip v1.2.1.zip
        sudo tar xvfz zlib-1.2.11.tar.gz
        sudo tar xvfz master.tar.gz
        if cd nginx-1.17.3
        then
                ./configure --with-http_ssl_module --with-http_v2_module --with-http_auth_request_module --add-module=../nginx-rtmp-module-1.2.1 --add-module=../nginx-goodies-nginx-sticky-module-ng-08a395c66e42 --with-zlib=../zlib-1.2.11 --with-cc-opt="-Wimplicit-fallthrough=0"
                sudo make install
        else
                echo "Unable to Build Nginx! Aborting."
                exit 1
        fi
else
        echo "Unable to Download Nginx due to missing /tmp! Aborting."
        exit 1
fi

# Grab Configuration
if cd $cwd/nginx
then
        sudo cp *.conf /usr/local/nginx/conf/
else
        echo "Unable to find downloaded Nginx config directory.  Aborting."
        exit 1
fi
# Enable SystemD
if cd $cwd/nginx
then
        sudo cp nginx-osp.service /etc/systemd/system/nginx-osp.service
        sudo systemctl daemon-reload
        sudo systemctl enable nginx-osp.service
else
        echo "Unable to find downloaded Nginx config directory. Aborting."
        exit 1
fi

if cd $cwd/gunicorn
then
        sudo cp osp.target /etc/systemd/system/
        sudo cp osp-worker@.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable osp.target
else
        echo "Unable to find downloaded Gunicorn config directory. Aborting."
        exit 1
fi

# Create HLS directory
sudo mkdir -p /var/www
sudo mkdir -p /var/www/live
sudo mkdir -p /var/www/videos
sudo mkdir -p /var/www/live-rec
sudo mkdir -p /var/www/images
sudo mkdir -p /var/www/live-adapt
sudo mkdir -p /var/www/stream-thumb

sudo chown -R www-data:www-data /var/www

sudo chown -R www-data:www-data /opt/osp
sudo chown -R www-data:www-data /opt/osp/.git

#Setup FFMPEG for recordings and Thumbnails
sudo add-apt-repository ppa:jonathonf/ffmpeg-4 -y
sudo apt-get update
sudo apt-get install ffmpeg -y

# Setup Logrotate
if cd /etc/logrotate.d
then
    sudo cp /opt/osp/setup/logrotate/* /etc/logrotate.d/
else
    sudo apt-get install logrorate
    if cd /etc/logrotate.d
    then
        sudo cp /opt/osp/setup/logrotate/* /etc/logrotate.d/
    else
        echo "Unable to setup logrotate"
    fi
fi
# Start Nginx
sudo systemctl start nginx-osp.service
echo "OSP Install Completed! Please copy /opt/osp/conf/config.py.dist to /opt/osp/conf/config.py, review the settings, and start the osp service by running typing sudo systemctl start osp.target"