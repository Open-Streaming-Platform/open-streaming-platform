#!/bin/bash
# 0.8.0 Upgrade Script

sudo sed -i '/#dbLocation/d' /opt/osp/conf/config.py
sudo sed -i '/# dbLocation/d' /opt/osp/conf/config.py
db=$(awk -F "=" '/dbLocation/ {print $2}' /opt/osp/conf/config.py | tr -d ' ' | cut -d ':' -f 1 )
db=${db#?}

echo ''
echo '**OSP Upgrader**'
echo 'This will upgrade OSP from 0.7.x to 0.8.x.'
echo ''
echo "Database is configured as: $db"
echo 'Note: SQLite is no longer supported and it is recommend if you are using it to migrate to MySQL/MariaDB before upgrading.'
read -p "Continue? (Y/N): " confirm && [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]] || exit 1

sudo systemctl stop osp.target
sudo systemctl stop nginx-osp
sudo rm /usr/local/nginx/conf/osp-*.conf
sudo systemctl stop ejabberd
sudo rm -rf /usr/local/ejabberd
echo ''
sudo cp /usr/local/nginx/conf/nginx.conf /usr/local/nginx/conf/nginx.conf.old
echo 'Your original nginx.conf file has been moved to /usr/local/nginx/conf/nginx.conf.old.  Please update the new nginx.conf file with any customizations before running.'
echo ''
sudo cp /opt/osp/conf/config.py /opt/osp/conf/config.py.old
echo 'Your original OSP config.py has been moved to /opt/osp/conf/config.py.old.  Please update the new config.py with any customizations before running.'
echo ''
echo 'Please run the osp-config.py installer and select Install > Install OSP - Single Server.  During the after the install process, you will need to transpose your original SQL user and password to the new config.py and restart osp.target'
exit 1