sudo mysql --database="osp" --execute="DROP TABLE alembic_version;"
sudo mkdir /tmp/osp
sudo mv /opt/osp/migrations/versions/* /tmp/osp
sudo pip3 install -r /opt/osp/setup/requirements.txt
sudo python3 manage.py db migrate
sudo python3 manage.py db upgrade
sudo mysql --database="osp" --execute="DROP TABLE alembic_version;"
sudo rm -rf /opt/osp/migrations/versions/*
sudo mv /tmp/osp/* /opt/osp/migrations/versions
sudo python3 manage.py db stamp head
sudo mysql --database="osp" --execute="update settings set systemTheme='Defaultv3';"
sudo bash osp-config.sh reset nginx
sudo bash osp-config.sh upgrade osp
sudo chown -R www-data:www-data /opt/osp
clear
echo "OSP 0.9.x Upgrade Complete!"