mysql --database="osp" --execute="DROP TABLE alembic_version;"
mkdir /tmp/osp
sudo mv /opt/osp/migrations/versions/* /tmp/osp
sudo pip3 install -r /opt/osp/setup/requirements.txt
python3 manage.py db migrate
python3 manage.py db upgrade
mysql --database="osp" --execute="DROP TABLE alembic_version;"
sudo rm -rf /opt/osp/migrations/versions/*
sudo mv /tmp/osp/* /opt/osp/migrations/versions
python3 manage.py db stamp head
mysql --database="osp" --execute="update settings set systemTheme='Defaultv3';"
sudo bash osp-config.sh reset nginx
sudo bash osp-config.sh upgrade osp
clear
echo "OSP 0.9.x Upgrade Complete!"