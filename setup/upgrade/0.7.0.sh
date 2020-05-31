#!/bin/bash
# 0.7.0 Upgrade Script
UPGRADELOG="/opt/osp/logs/0.7.0-upgrade.log"

wget -O "/tmp/ejabberd-20.04-linux-x64.run" "https://www.process-one.net/downloads/downloads-action.php?file=/20.04/ejabberd-20.04-linux-x64.run" >> $UPGRADELOG 2>&1
sudo chmod +x /tmp/ejabberd-20.04-linux-x64.run $UPGRADELOG 2>&1
/tmp/ejabberd-20.04-linux-x64.run ----unattendedmodeui none --mode unattended --prefix /usr/local/ejabberd --cluster 0 >> $UPGRADELOG 2>&1
mkdir /usr/local/ejabberd/conf >> $UPGRADELOG 2>&1
cp /opt/osp/setup/ejabberd/ejabberd.yml /usr/local/ejabberd/conf/ejabberd.yml >> $UPGRADELOG 2>&1
cp /usr/local/ejabberd/bin/ejabberd.service /etc/systemd/system/ejabberd.service >> $UPGRADELOG 2>&1
user_input=$(\
  dialog --nocancel --title "Setting up Ejabberd" \
         --inputbox "Enter your Site Address (Per OSP Admin Settings):" 8 80 \
  3>&1 1>&2 2>&3 3>&-)
sudo sed -i "s/CHANGEME/$user_input/g" /usr/local/ejabberd/conf/ejabberd.yml>> $UPGRADELOG 2>&1
sudo systemctl daemon-reload >> $UPGRADELOG 2>&1
sudo systemctl enable ejabberd >> $UPGRADELOG 2>&1
sudo systemctl start ejabberd >> $UPGRADELOG 2>&1

if grep -Fxq "ejabberdHost" /opt/osp/conf/config.py
then
    echo "Config Lines Exist"
else
  echo '# EJabberD Configuration' >> /opt/osp/conf/config.py
  echo 'ejabberdAdmin = "admin"' >> /opt/osp/conf/config.py
  echo 'ejabberdPass = "CHANGE_EJABBERD_PASS"' >> /opt/osp/conf/config.py
  echo 'ejabberdHost = "localhost"' >> /opt/osp/conf/config.py
  ADMINPASS=$( cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1 )
  sed -i "s/CHANGE_EJABBERD_PASS/$ADMINPASS/" /opt/osp/conf/config.py >> $UPGRADELOG 2>&1
  /usr/local/ejabberd/bin/ejabberdctl register admin localhost $ADMINPASS >> $UPGRADELOG 2>&1
fi

sudo systemctl restart nginx-osp
sudo systemctl restart osp.target
