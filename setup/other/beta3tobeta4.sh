sudo rm /etc/systemd/system/osp.service
cd ..
sudo cp /usr/local/nginx/conf/nginx.conf /usr/local/nginx/conf/nginx.conf.old
sudo bash setup-osp.sh
cd ..
sudo python3 manage.py db init
sudo bash dbUpgrade.sh