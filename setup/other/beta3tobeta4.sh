sudo rm /etc/systemd/system/osp.service
sudo apt-get remove gunicorn3
sudo pip3 install --upgrade pip
sudo pip3 uninstall gunicorn -y
cd ..
sudo cp /usr/local/nginx/conf/nginx.conf /usr/local/nginx/conf/nginx.conf.old
sudo bash setup-osp.sh
sudo pip3 install gunicorn
sudo pip3 uninstall flask-security
sudo pip3 install flask-security-too
cd ..
sudo mkdir -p /opt/osp/cache
sudo python3 manage.py db init
sudo bash dbUpgrade.sh
