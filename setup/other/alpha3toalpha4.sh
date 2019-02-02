sudo pip freeze > /tmp/py2modules.txt
sudo pip uninstall -y -r /tmp/py2modules.txt
sudo apt-get remove gunicorn -y
sudo apt-get install python3 -y
sudo apt-get remove python2.7 -y
sudo apt-get install python3-pip -y
cd ..
sudo pip3 install -y -r requirements.txt
sudo apt-get install gunicorn3 -y
cd gunicorn
sudo cp osp.service /lib/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable osp.service
sudo systemctl stop osp
sudo systemctl start osp
