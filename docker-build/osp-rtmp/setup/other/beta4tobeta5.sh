loglocation=/opt/osp/logs/beta5Upgrade.log

echo Creating Backup of /usr/local/nginx/conf/nginx.conf as /usr/local/nginx/conf/nginx.conf.old
sudo cp /usr/local/nginx/conf/nginx.conf /usr/local/nginx/conf/nginx.conf.old > $loglocation
echo Replacing Nginx Conf Files
sudo cp /opt/osp/setup/nginx/*.conf /usr/local/nginx/conf/
echo Setting Ownership of /opt/osp to www-data
sudo chown -R www-data:www-data /opt/osp >> $loglocation
echo Upgrading Dependencies
sudo pip3 install -r /opt/osp/setup/requirements.txt >> $loglocation
echo Performing DB Migration
cd /opt/osp >> $loglocation
echo debugMode=False >> /opt/osp/conf/config.py
sudo python3 manage.py db init >> $loglocation
sudo python3 manage.py db migrate >> $loglocation
sudo python3 manage.py db upgrade >> $loglocation
sudo systemctl restart osp.target >> $loglocation
sudo systemctl restart nginx-osp >> $loglocation
echo Upgrade Completed.  Please check $loglocation for any errors.
