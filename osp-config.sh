#!/bin/bash
# OSP Control Script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OSPLOG="/var/log/osp/installer.log"
VERSION=$(<version)

DIALOG_CANCEL=1
DIALOG_ESC=255
HEIGHT=0
WIDTH=0

archu=$( uname -r | grep -i "arch")
if [[ "$archu" = *"arch"* ]]
then
  arch=true
  web_root='/srv/http'
  http_user='http'
else
  arch=false
  web_root='/var/www'
  http_user='www-data'
fi

#######################################################
# Check Requirements
#######################################################
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

command -v dialog >/dev/null 2>&1 || { echo >&2 "Dialog is required but it's not installed. (apt-get dialog/packman -S dialog)  Aborting."; exit 1; }
command -v sudo >/dev/null 2>&1 || { echo >&2 "Sudo is required but it's not installed. (apt-get sudo/packman -S sudo)  Aborting."; exit 1; }

#######################################################
# Script Functions
#######################################################

display_result() {
  dialog --title "$1" \
    --no-collapse \
    --msgbox "$result" 20 70
}

reset_ejabberd() {
  echo 5 | dialog --title "Reset eJabberd Configuration" --gauge "Stopping eJabberd" 10 70 0
  sudo systemctl stop ejabberd >> $OSPLOG 2>&1
  echo 10 | dialog --title "Reset eJabberd Configuration" --gauge "Removing eJabberd" 10 70 0
  sudo rm -rf /usr/local/ejabberd >> $OSPLOG 2>&1
  echo 20 | dialog --title "Reset eJabberd Configuration" --gauge "Downloading eJabberd" 10 70 0
  sudo wget -O "/tmp/ejabberd-20.12-linux-x64.run" "https://www.process-one.net/downloads/downloads-action.php?file=/20.12/ejabberd-20.12-linux-x64.run" >> $OSPLOG 2>&1
  sudo chmod +x /tmp/ejabberd-20.12-linux-x64.run >> $OSPLOG 2>&1
  echo 30 | dialog --title "Reset eJabberd Configuration" --gauge "Reinstalling eJabberd" 10 70 0
  sudo /tmp/ejabberd-20.12-linux-x64.run ----unattendedmodeui none --mode unattended --prefix /usr/local/ejabberd --cluster 0 >> $OSPLOG 2>&1
  echo 50 | dialog --title "Reset eJabberd Configuration" --gauge "Replacing Admin Creds in Config.py" 10 70 0
  ADMINPASS=$( cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1 )
  sudo sed -i '/^ejabberdPass/d' /opt/osp/conf/config.py >> $OSPLOG 2>&1
  sudo sed -i '/^ejabberdHost/d' /opt/osp/conf/config.py >> $OSPLOG 2>&1
  sudo sed -i '/^ejabberdAdmin/d' /opt/osp/conf/config.py >> $OSPLOG 2>&1
  sudo echo 'ejabberdAdmin = "admin"' >> /opt/osp/conf/config.py
  sudo echo 'ejabberdHost = "localhost"' >> /opt/osp/conf/config.py
  sudo echo 'ejabberdPass = "CHANGE_EJABBERD_PASS"' >> /opt/osp/conf/config.py
  sudo sed -i "s/CHANGE_EJABBERD_PASS/$ADMINPASS/" /opt/osp/conf/config.py >> $OSPLOG 2>&1
  echo 60 | dialog --title "Reset eJabberd Configuration" --gauge "Install eJabberd Configuration File" 10 70 0
  sudo mkdir /usr/local/ejabberd/conf >> $OSPLOG 2>&1
  sudo cp /opt/osp/installs/ejabberd/setup/ejabberd.yml /usr/local/ejabberd/conf/ejabberd.yml >> $OSPLOG 2>&1
  sudo cp /opt/osp/installs/ejabberd/setup/inetrc /usr/local/ejabberd/conf/inetrc >> $OSPLOG 2>&1
  sudo cp /opt/osp/installs/ejabberd/setup/auth_osp.py /usr/local/ejabberd/conf/auth_osp.py >> $OSPLOG 2>&1
  sudo cp /usr/local/ejabberd/bin/ejabberd.service /etc/systemd/system/ejabberd.service >> $OSPLOG 2>&1
  user_input=$(\
  dialog --nocancel --title "Setting up eJabberd" \
         --inputbox "Enter your Site Address (Must match FQDN):" 8 80 \
  3>&1 1>&2 2>&3 3>&-)
  echo 80 | dialog --title "Reset eJabberd Configuration" --gauge "Updating eJabberd Config File" 10 70 0
  sudo sed -i "s/CHANGEME/$user_input/g" /usr/local/ejabberd/conf/ejabberd.yml >> $OSPLOG 2>&1
  echo 85 | dialog --title "Reset eJabberd Configuration" --gauge "Restarting eJabberd" 10 70 0
  sudo systemctl daemon-reload >> $OSPLOG 2>&1
  sudo systemctl enable ejabberd >> $OSPLOG 2>&1
  sudo systemctl start ejabberd >> $OSPLOG 2>&1
  echo 90 | dialog --title "Reset eJabberd Configuration" --gauge "Setting eJabberd Local Admin" 10 70 0
  sudo /usr/local/ejabberd/bin/ejabberdctl register admin localhost $ADMINPASS >> $OSPLOG 2>&1
  sudo /usr/local/ejabberd/bin/ejabberdctl change_password admin localhost $ADMINPASS >> $OSPLOG 2>&1
  echo 95 | dialog --title "Reset eJabberd Configuration" --gauge "Restarting OSP" 10 70 0
  sudo systemctl restart osp.target >> $OSPLOG 2>&1
}

upgrade_db() {
  UPGRADELOG="/opt/osp/logs/upgrade.log"
  echo 0 | dialog --title "Upgrading Database" --gauge "Stopping OSP" 10 70 0
  sudo systemctl stop osp.target >> $OSPLOG 2>&1
  cd /opt/osp
  echo 15 | dialog --title "Upgrading Database" --gauge "Upgrading Database" 10 70 0
  python3 manage.py db init >> $OSPLOG 2>&1
  echo 25 | dialog --title "Upgrading Database" --gauge "Upgrading Database" 10 70 0
  python3 manage.py db migrate >> $OSPLOG 2>&1
  echo 50 | dialog --title "Upgrading Database" --gauge "Upgrading Database" 10 70 0
  python3 manage.py db upgrade >> $OSPLOG 2>&1
  echo 75 | dialog --title "Upgrading Database" --gauge "Starting OSP" 10 70 0
  sudo systemctl start osp.target >> $OSPLOG 2>&1
  echo 100 | dialog --title "Upgrading Database" --gauge "Complete" 10 70 0
  cd $DIR
}

upgrade_osp() {
   UPGRADELOG="/opt/osp/logs/upgrade.log"
   echo 0 | dialog --title "Upgrading OSP" --gauge "Pulling Git Repo" 10 70 0
   sudo git stash >> $OSPLOG 2>&1
   sudo git pull >> $OSPLOG 2>&1
   echo 15 | dialog --title "Upgrading OSP" --gauge "Setting /opt/osp Ownership" 10 70 0
   sudo chown -R $http_user:$http_user /opt/osp >> $OSPLOG 2>&1
   echo 25 | dialog --title "Upgrading OSP" --gauge "Stopping OSP" 10 70 0
   sudo systemctl stop osp.target >> $OSPLOG 2>&1
   echo 30 | dialog --title "Upgrading OSP" --gauge "Stopping Nginx" 10 70 0
   sudo systemctl stop nginx-osp >> $OSPLOG 2>&1
   echo 35 | dialog --title "Upgrading OSP" --gauge "Installing Python Dependencies" 10 70 0
   sudo pip3 install -r /opt/osp/setup/requirements.txt >> $OSPLOG 2>&1
   echo 45 | dialog --title "Upgrading OSP" --gauge "Upgrading Nginx-RTMP Configurations" 10 70 0
   sudo cp /opt/osp/setup/nginx/osp-rtmp.conf /usr/local/nginx/conf >> $OSPLOG 2>&1
   sudo cp /opt/osp/setup/nginx/osp-redirects.conf /usr/local/nginx/conf >> $OSPLOG 2>&1
   sudo cp /opt/osp/setup/nginx/osp-socketio.conf /usr/local/nginx/conf >> $OSPLOG 2>&1
   echo 50 | dialog --title "Upgrading OSP" --gauge "Upgrading Database" 10 70 0
   python3 manage.py db init >> $OSPLOG 2>&1
   echo 55 | dialog --title "Upgrading OSP" --gauge "Upgrading Database" 10 70 0
   python3 manage.py db migrate >> $OSPLOG 2>&1
   echo 65 | dialog --title "Upgrading OSP" --gauge "Upgrading Database" 10 70 0
   python3 manage.py db upgrade >> $OSPLOG 2>&1
   echo 75 | dialog --title "Upgrading OSP" --gauge "Starting OSP" 10 70 0
   sudo systemctl start osp.target >> $OSPLOG 2>&1
   echo 90 | dialog --title "Upgrading OSP" --gauge "Starting Nginx" 10 70 0
   sudo systemctl start nginx-osp >> $OSPLOG 2>&1
   echo 100 | dialog --title "Upgrading OSP" --gauge "Complete" 10 70 0
}

install_prereq() {
    echo 10 | dialog --title "Installing Prereqs" --gauge "Installing Preqs - Debian Based" 10 70 0
    # Get Deb Dependencies
    sudo apt-get install wget build-essential libpcre3 libpcre3-dev libssl-dev unzip libpq-dev curl git -y >> $OSPLOG 2>&1
    # Setup Python
    echo 50 | dialog --title "Installing Prereqs" --gauge "Installing Python3 Requirements - Debian Based" 10 70 0
    sudo apt-get install python3 python3-pip uwsgi-plugin-python3 python3-dev python3-setuptools -y >> $OSPLOG 2>&1
    sudo pip3 install wheel >> $OSPLOG 2>&1
}

install_ffmpeg() {
  #Setup FFMPEG for recordings and Thumbnails
  echo 10 | dialog --title "Installing FFMPEG" --gauge "Installing FFMPEG" 10 70 0
  echo 45 | dialog --title "Installing FFMPEG" --gauge "Installing FFMPEG" 10 70 0
  sudo add-apt-repository ppa:jonathonf/ffmpeg-4 -y >> $OSPLOG 2>&1
  echo 75 | dialog --title "Installing FFMPEG" --gauge "Installing FFMPEG" 10 70 0
  sudo apt-get update >> $OSPLOG 2>&1
  echo 90 | dialog --title "Installing FFMPEG" --gauge "Installing FFMPEG" 10 70 0
  sudo apt-get install ffmpeg -y >> $OSPLOG 2>&1
}

install_mysql(){
  SQLPASS=$( cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1 )
  echo 10 | dialog --title "Installing MySQL" --gauge "Installing MySQL Server" 10 70 0
  sudo apt-get install mysql-server -y >> $OSPLOG 2>&1
  echo 25 | dialog --title "Installing MySQL" --gauge "Copying MySQL Configuration" 10 70 0
  sudo cp $DIR/setup/mysql/mysqld.cnf /etc/mysql/my.cnf >> $OSPLOG 2>&1
  echo 50 | dialog --title "Installing MySQL" --gauge "Restarting MySQL Server" 10 70 0
  sudo systemctl restart mysql >> $OSPLOG 2>&1
  echo 75 | dialog --title "Installing MySQL" --gauge "Building Database" 10 70 0
  sudo mysql -e "create database osp" >> $OSPLOG 2>&1
  sudo mysql -e "CREATE USER 'osp'@'localhost' IDENTIFIED BY '$SQLPASS'" >> $OSPLOG 2>&1
  sudo mysql -e "GRANT ALL PRIVILEGES ON osp.* TO 'osp'@'localhost'" >> $OSPLOG 2>&1
  sudo mysql -e "flush privileges" >> $OSPLOG 2>&1
  echo 100 | dialog --title "Installing MySQL" --gauge "Updating OSP Configuration File" 10 70 0
  sudo sed -i "s/sqlpass/$SQLPASS/g" /opt/osp-rtmp/conf/config.py >> $OSPLOG 2>&1
  sudo sed -i "s/sqlpass/$SQLPASS/g" /opt/osp/conf/config.py >> $OSPLOG 2>&1
}

install_nginx_core() {
  install_prereq
  # Build Nginx with RTMP module
  echo 10 | dialog --title "Installing Nginx-Core" --gauge "Downloading Nginx Source" 10 70 0
  if cd /tmp
  then
          echo 5 | dialog --title "Installing Nginx-Core" --gauge "Downloading Nginx Source" 10 70 0
          sudo wget -q "http://nginx.org/download/nginx-1.17.3.tar.gz" >> $OSPLOG 2>&1
          echo 15 | dialog --title "Installing Nginx-Core" --gauge "Downloading Required Modules" 10 70 0
          sudo wget -q "https://github.com/arut/nginx-rtmp-module/archive/v1.2.1.zip" >> $OSPLOG 2>&1
          echo 20 | dialog --title "Installing Nginx-Core" --gauge "Downloading Required Modules" 10 70 0
          sudo wget -q "http://www.zlib.net/zlib-1.2.11.tar.gz" >> $OSPLOG 2>&1
          echo 25 | dialog --title "Installing Nginx-Core" --gauge "Downloading Required Modules" 10 70 0
          sudo wget -q "https://bitbucket.org/nginx-goodies/nginx-sticky-module-ng/get/master.tar.gz" >> $OSPLOG 2>&1
          echo 30 | dialog --title "Installing Nginx-Core" --gauge "Decompressing Nginx Source and Modules" 10 70 0
          sudo tar xfz nginx-1.17.3.tar.gz >> $OSPLOG 2>&1
          sudo unzip -qq -o v1.2.1.zip >> $OSPLOG 2>&1
          sudo tar xfz zlib-1.2.11.tar.gz >> $OSPLOG 2>&1
          sudo tar xfz master.tar.gz >> $OSPLOG 2>&1
          echo 35 | dialog --title "Installing Nginx-Core" --gauge "Building Nginx from Source" 10 70 0
          if cd nginx-1.17.3
          then
                  ./configure --with-http_ssl_module --with-http_v2_module --with-http_auth_request_module --add-module=../nginx-rtmp-module-1.2.1 --add-module=../nginx-goodies-nginx-sticky-module-ng-08a395c66e42 --with-zlib=../zlib-1.2.11 --with-cc-opt="-Wimplicit-fallthrough=0" >> $OSPLOG 2>&1
                  echo 50 | dialog --title "Installing Nginx-Core" --gauge "Installing Nginx" 10 70 0
                  sudo make install >> $OSPLOG 2>&1
          else
                  echo "Unable to Build Nginx! Aborting."
                  exit 1
          fi
  else
          echo "Unable to Download Nginx due to missing /tmp! Aborting."
          exit 1
  fi

  # Grab Configuration
  echo 65 | dialog --title "Installing Nginx-Core" --gauge "Copying Nginx Config Files" 10 70 0

  sudo cp $DIR/installs/nginx-core/nginx.conf /usr/local/nginx/conf/ >> $OSPLOG 2>&1
  sudo cp $DIR/installs/nginx-core/mime.types /usr/local/nginx/conf/ >> $OSPLOG 2>&1
  sudo mkdir /usr/local/nginx/conf/locations >> $OSPLOG 2>&1
  sudo mkdir /usr/local/nginx/conf/upstream >> $OSPLOG 2>&1
  sudo mkdir /usr/local/nginx/conf/servers >> $OSPLOG 2>&1
  sudo mkdir /usr/local/nginx/conf/services >> $OSPLOG 2>&1

  # Enable SystemD
  echo 75 | dialog --title "Installing Nginx-Core" --gauge "Setting up Nginx SystemD" 10 70 0

  sudo cp $DIR/installs/nginx-core/nginx-osp.service /etc/systemd/system/nginx-osp.service >> $OSPLOG 2>&1
  sudo systemctl daemon-reload >> $OSPLOG 2>&1
  sudo systemctl enable nginx-osp.service >> $OSPLOG 2>&1

  install_ffmpeg

  # Create HLS directory
  echo 80 | dialog --title "Installing Nginx-Core" --gauge "Creating OSP Video Directories" 10 70 0
  sudo mkdir -p "$web_root" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/live" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/videos" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/live-adapt" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/stream-thumb" >> $OSPLOG 2>&1

  echo 90 | dialog --title "Installing Nginx-Core" --gauge "Setting Ownership of OSP Video Directories" 10 70 0
  sudo chown -R "$http_user:$http_user" "$web_root" >> $OSPLOG 2>&1

  # Start Nginx
  echo 100 | dialog --title "Installing Nginx-Core" --gauge "Starting Nginx" 10 70 0
  sudo systemctl start nginx-osp.service >> $OSPLOG 2>&1

}

install_osp_rtmp() {
  echo 10 | dialog --title "Installing OSP-RTMP" --gauge "Intalling Prereqs" 10 70 0
  install_prereq
  echo 25 | dialog --title "Installing OSP-RTMP" --gauge "Installing Requirements.txt" 10 70 0
  sudo pip3 install -r $DIR/installs/osp-rtmp/setup/requirements.txt >> $OSPLOG 2>&1

  echo 40 | dialog --title "Installing OSP-RTMP" --gauge "Setting Up Nginx Configs" 10 70 0
  sudo cp $DIR/installs/osp-rtmp/setup/nginx/servers/*.conf /usr/local/nginx/conf/servers >> $OSPLOG 2>&1
  sudo cp $DIR/installs/osp-rtmp/setup/nginx/services/*.conf /usr/local/nginx/conf/services >> $OSPLOG 2>&1

  echo 50 | dialog --title "Installing OSP-RTMP" --gauge "Install OSP-RTMP Application" 10 70 0
  sudo mkdir /opt/osp-rtmp >> $OSPLOG 2>&1

  # Setup Nginx-RTMP Socket Directory
  sudo cp -R $DIR/installs/osp-rtmp/* /opt/osp-rtmp >> $OSPLOG 2>&1
  sudo mkdir /opt/osp-rtmp/rtmpsocket >> $OSPLOG 2>&1
  sudo chown -R www-data:www-data /opt/osp-rtmp/rtmpsocket >> $OSPLOG 2>&1

echo 75 | dialog --title "Installing OSP-RTMP" --gauge "Installing SystemD File" 10 70 0
  sudo cp $DIR/installs/osp-rtmp/setup/gunicorn/osp-rtmp.service /etc/systemd/system/osp-rtmp.service >> $OSPLOG 2>&1
  sudo systemctl daemon-reload >> $OSPLOG 2>&1
  sudo systemctl enable osp-rtmp.service >> $OSPLOG 2>&1
}

install_redis() {
  # Install Redis
  echo 50 | dialog --title "Installing Redis" --gauge "Installing Redis Server" 10 70 0
  sudo apt-get install redis -y >> $OSPLOG 2>&1
  echo 25 | dialog --title "Installing Redis" --gauge "Configuring Redis" 10 70 0
  sudo sed -i 's/appendfsync everysec/appendfsync no/' /etc/redis/redis.conf >> $OSPLOG 2>&1
}

install_osp_edge () {

  user_input=$(\
  dialog --nocancel --title "Setting up OSP-Edge" \
         --inputbox "Enter your OSP-RTMP IP Address:" 8 80 \
  3>&1 1>&2 2>&3 3>&-)

  core_input=$(\
  dialog --nocancel --title "Setting up OSP-Edge" \
         --inputbox "Enter your OSP-RTMP IP Address:" 8 80 \
  3>&1 1>&2 2>&3 3>&-)

  # Grab Configuration
  echo 10 | dialog --title "Installing OSP-Edge" --gauge "Installing Configuration Files" 10 70 0
  sudo cp $DIR/installs/osp-edge/setup/nginx/locations/osp-edge-redirects.conf /usr/local/nginx/conf/locations >> $OSPLOG 2>&1
  sudo cp $DIR/installs/osp-edge/setup/nginx/servers/osp-edge-servers.conf /usr/local/nginx/conf/servers >> $OSPLOG 2>&1
  sudo cp $DIR/installs/osp-edge/setup/nginx/services/osp-edge-rtmp.conf /usr/local/nginx/conf/services >> $OSPLOG 2>&1

  # Setup Configuration with IP
  echo 40 | dialog --title "Installing OSP-Edge" --gauge "Installing Configuration Files" 10 70 0
  sed -i "s/CHANGEME/$user_input/g" /usr/local/nginx/conf/services/osp-edge-rtmp.conf >> $OSPLOG 2>&1
  sed -i "s/CHANGEME/$core_input/g" /usr/local/nginx/conf/servers/osp-edge-servers.conf >> $OSPLOG 2>&1

  # Make OSP-Edge Directory for RTMP sockets
  echo 60 | dialog --title "Installing OSP-Edge" --gauge "Creating OSP-Edge Directories" 10 70 0
  sudo mkdir /opt/osp-edge >> $OSPLOG 2>&1
  sudo mkdir /opt/osp-edge/rtmpsocket >> $OSPLOG 2>&1
  sudo chown -R www-data:www-data /opt/osp-edge/rtmpsocket >> $OSPLOG 2>&1

  # Create HLS directory
  sudo mkdir -p /var/www >> $OSPLOG 2>&1
  sudo mkdir -p /var/www/live >> $OSPLOG 2>&1
  sudo mkdir -p /var/www/live-adapt >> $OSPLOG 2>&1

  sudo chown -R www-data:www-data /var/www >> $OSPLOG 2>&1

  echo 75 | dialog --title "Installing OSP-Edge" --gauge "Setting up FFMPEG" 10 70 0

  # Start Nginx
  echo 90 | dialog --title "Installing OSP-Edge" --gauge "Restarting Nginx Core" 10 70 0
  sudo systemctl restart nginx-osp.service >> $OSPLOG 2>&1
}

install_ejabberd() {
  echo 5 | dialog --title "Installing ejabberd" --gauge "Installing Prereqs" 10 70 0
  install_prereq
  sudo pip3 install requests >> $OSPLOG 2>&1

  # Install ejabberd
  echo 10 | dialog --title "Installing ejabberd" --gauge "Downloading ejabberd" 10 70 0
  sudo wget -O "/tmp/ejabberd-20.12-linux-x64.run" "https://www.process-one.net/downloads/downloads-action.php?file=/20.12/ejabberd-20.12-linux-x64.run" >> $OSPLOG 2>&1
  echo 20 | dialog --title "Installing ejabberd" --gauge "Installing ejabberd" 10 70 0
  sudo chmod +x /tmp/ejabberd-20.12-linux-x64.run >> $OSPLOG 2>&1
  /tmp/ejabberd-20.12-linux-x64.run ----unattendedmodeui none --mode unattended --prefix /usr/local/ejabberd --cluster 0 >> $OSPLOG 2>&1
  echo 35 | dialog --title "Installing ejabberd" --gauge "Installing Configuration Files" 10 70 0
  mkdir /usr/local/ejabberd/conf >> $OSPLOG 2>&1
  sudo cp $DIR/installs/ejabberd/setup/ejabberd.yml /usr/local/ejabberd/conf/ejabberd.yml >> $OSPLOG 2>&1
  sudo cp $DIR/installs/ejabberd/setup/auth_osp.py /usr/local/ejabberd/conf/auth_osp.py >> $OSPLOG 2>&1
  sudo cp $DIR/installs/ejabberd/setup/inetrc /usr/local/ejabberd/conf/inetrc >> $OSPLOG 2>&1
  sudo cp /usr/local/ejabberd/bin/ejabberd.service /etc/systemd/system/ejabberd.service >> $OSPLOG 2>&1
  user_input=$(\
  dialog --nocancel --title "Setting up eJabberd" \
         --inputbox "Enter your Site Address (Must match FQDN):" 8 80 \
  3>&1 1>&2 2>&3 3>&-)
  echo 65 | dialog --title "Installing ejabberd" --gauge "Setting Up ejabberd Configuration" 10 70 0
  sudo sed -i "s/CHANGEME/$user_input/g" /usr/local/ejabberd/conf/ejabberd.yml >> $OSPLOG 2>&1
  echo 85 | dialog --title "Installing ejabberd" --gauge "Starting ejabberd" 10 70 0
  sudo systemctl daemon-reload >> $OSPLOG 2>&1
  sudo systemctl enable ejabberd >> $OSPLOG 2>&1
  sudo systemctl start ejabberd >> $OSPLOG 2>&1
  echo 95 | dialog --title "Installing ejabberd" --gauge "Installing Nginx File" 10 70 0
  sudo cp $DIR/installs/ejabberd/setup/nginx/locations/ejabberd.conf /usr/local/nginx/conf/locations/ >> $OSPLOG 2>&1
}

generate_ejabberd_admin() {
  ADMINPASS=$( cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1 )
  sed -i "s/CHANGE_EJABBERD_PASS/$ADMINPASS/" /opt/osp/conf/config.py >> $OSPLOG 2>&1
  sudo sed -i "s/CHANGEME/$user_input/g" /usr/local/ejabberd/conf/ejabberd.yml >> $OSPLOG 2>&1
  sudo /usr/local/ejabberd/bin/ejabberdctl register admin localhost $ADMINPASS >> $OSPLOG 2>&1
  sudo /usr/local/ejabberd/bin/ejabberdctl change_password admin localhost $ADMINPASS >> $OSPLOG 2>&1
  sudo systemctl restart ejabberd
}

install_osp() {
  cwd=$PWD

  echo "Starting OSP Install" >> $OSPLOG 2>&1
  echo 0 | dialog --title "Installing OSP" --gauge "Installing Linux Dependencies" 10 70 0

  install_prereq
  sudo pip3 install -r $DIR/setup/requirements.txt >> $OSPLOG 2>&1

  # Setup OSP Directory
  echo 20 | dialog --title "Installing OSP" --gauge "Setting up OSP Directory" 10 70 0
  mkdir -p /opt/osp >> $OSPLOG 2>&1
  sudo cp -rf -R $DIR/* /opt/osp >> $OSPLOG 2>&1
  sudo cp -rf -R $DIR/.git /opt/osp >> $OSPLOG 2>&1

  echo 50 | dialog --title "Installing OSP" --gauge "Setting up Gunicorn SystemD" 10 70 0
  if cd $DIR/setup/gunicorn
  then
          sudo cp $DIR/setup/gunicorn/osp.target /etc/systemd/system/ >> $OSPLOG 2>&1
          sudo cp $DIR/setup/gunicorn/osp-worker@.service /etc/systemd/system/ >> $OSPLOG 2>&1
          sudo systemctl daemon-reload >> $OSPLOG 2>&1
          sudo systemctl enable osp.target >> $OSPLOG 2>&1
  else
          echo "Unable to find downloaded Gunicorn config directory. Aborting." >> $OSPLOG 2>&1
          exit 1
  fi

  sudo cp $DIR/setup/nginx/locations/* /usr/local/nginx/conf/locations >> $OSPLOG 2>&1
  sudo cp $DIR/setup/nginx/upstream/* /usr/local/nginx/conf/upstream >> $OSPLOG 2>&1

  # Create HLS directory
  echo 60 | dialog --title "Installing OSP" --gauge "Creating OSP Video Directories" 10 70 0
  sudo mkdir -p "$web_root" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/live" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/videos" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/images" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/live-adapt" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/stream-thumb" >> $OSPLOG 2>&1

  echo 70 | dialog --title "Installing OSP" --gauge "Setting Ownership of OSP Video Directories" 10 70 0
  sudo chown -R "$http_user:$http_user" "$web_root" >> $OSPLOG 2>&1

  sudo chown -R "$http_user:$http_user" /opt/osp >> $OSPLOG 2>&1
  sudo chown -R "$http_user:$http_user" /opt/osp/.git >> $OSPLOG 2>&1

  # Setup Logrotate
  echo 90 | dialog --title "Installing OSP" --gauge "Setting Up Log Rotation" 10 70 0
  if cd /etc/logrotate.d
  then
      sudo cp /opt/osp/setup/logrotate/* /etc/logrotate.d/ >> $OSPLOG 2>&1
  else
      sudo apt-get install logrorate >> $OSPLOG 2>&1
      if cd /etc/logrotate.d
      then
          sudo cp /opt/osp/setup/logrotate/* /etc/logrotate.d/ >> $OSPLOG 2>&1
      else
          echo "Unable to setup logrotate" >> $OSPLOG 2>&1
      fi
  fi
}

upgrade_osp() {
  if cd /opt/osp
  then
    sudo git pull >> $OSPLOG 2>&1
    sudo cp -rf /opt/osp/setup/nginx/locations/* /usr/local/nginx/conf/locations >> $OSPLOG 2>&1
    sudo cp -rf /opt/osp/setup/nginx/upstream/* /usr/local/nginx/conf/upstream >> $OSPLOG 2>&1
  else
    echo "Error: /opt/osp Does not Exist" >> $OSPLOG 2>&1
  fi
}

upgrade_rtmp() {
  sudo git pull >> $OSPLOG 2>&1
  sudo pip3 install -r $DIR/installs/osp-rtmp/setup/requirements.txt >> $OSPLOG 2>&1
  sudo cp -rf $DIR/installs/osp-rtmp/setup/nginx/servers/*.conf /usr/local/nginx/conf/servers >> $OSPLOG 2>&1
  sudo cp -rf $DIR/installs/osp-rtmp/setup/nginx/services/*.conf /usr/local/nginx/conf/services >> $OSPLOG 2>&1
  sudo cp -R $DIR/installs/osp-rtmp/* /opt/osp-rtmp >> $OSPLOG 2>&1
}

upgrade_ejabberd() {
  sudo git pull >> $OSPLOG 2>&1
  sudo cp -rf $DIR/installs/ejabberd/setup/auth_osp.py /usr/local/ejabberd/conf/auth_osp.py >> $OSPLOG 2>&1
  sudo cp -rf $DIR/installs/ejabberd/setup/nginx/locations/ejabberd.conf /usr/local/nginx/conf/locations/ >> $OSPLOG 2>&1
}

##########################################################
# Menu Options
##########################################################
install_menu() {
    while true; do
    exec 3>&1
    selection=$(dialog \
      --backtitle "Open Streaming Platform - $VERSION" \
      --title "Menu" \
      --clear \
      --cancel-label "Exit" \
      --menu "Please select:" $HEIGHT $WIDTH 7 \
      "1" "Install OSP - Single Server" \
      "2" "Install OSP-Core" \
      "3" "Install OSP-RTMP" \
      "4" "Install OSP-Edge" \
      "5" "Install eJabberd" \
      2>&1 1>&3)
    exit_status=$?
    exec 3>&-
    case $exit_status in
      $DIALOG_CANCEL)
        clear
        echo "Program terminated."
        exit
        ;;
      $DIALOG_ESC)
        clear
        echo "Program aborted." >&2
        exit 1
        ;;
    esac
    case $selection in
      0 )
        clear
        echo "Program terminated."
        ;;
      1 )
        echo 10 | dialog --title "Installing OSP" --gauge "Installing Nginx Core" 10 70 0
        install_nginx_core
        echo 20 | dialog --title "Installing OSP" --gauge "Installing Redis" 10 70 0
        install_redis
        echo 30 | dialog --title "Installing OSP" --gauge "Installing ejabberd" 10 70 0
        install_ejabberd
        echo 40 | dialog --title "Installing OSP" --gauge "Installing OSP-RTMP" 10 70 0
        install_osp_rtmp
        echo 60 | dialog --title "Installing OSP" --gauge "Installing OSP Core" 10 70 0
        install_osp
        echo 65 | dialog --title "Installing OSP" --gauge "Setting Up Configuration Files" 10 70 0
        sudo cp /opt/osp-rtmp/conf/config.py.dist /opt/osp-rtmp/conf/config.py >> $OSPLOG 2>&1
        sudo cp /opt/osp/conf/config.py.dist /opt/osp/conf/config.py >> $OSPLOG 2>&1
        echo 75 | dialog --title "Installing OSP" --gauge "Setting up ejabberd" 10 70 0
        generate_ejabberd_admin
        echo 80 | dialog --title "Installing OSP" --gauge "Installing MySQL" 10 70 0
        install_mysql
        echo 85 | dialog --title "Installing OSP" --gauge "Restarting Nginx Core" 10 70 0
        sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
        echo 90 | dialog --title "Installing OSP" --gauge "Starting OSP Core" 10 70 0
        sudo systemctl start osp.target >> $OSPLOG 2>&1
        upgrade_db
        echo 95 | dialog --title "Installing OSP" --gauge "Starting OSP-RTMP" 10 70 0
        sudo systemctl start osp-rtmp >> $OSPLOG 2>&1
        result=$(echo "OSP Install Completed! \n\nVisit http:\\FQDN to configure\n\nInstall Log can be found at /opt/osp/logs/install.log")
        display_result "Install OSP"
        ;;
      2 )
        echo 30 | dialog --title "Installing OSP" --gauge "Installing Nginx Core" 10 70 0
        install_nginx_core
        echo 60 | dialog --title "Installing OSP" --gauge "Installing OSP Core" 10 70 0
        install_osp
        echo 90 | dialog --title "Installing OSP" --gauge "Restarting Nginx Core" 10 70 0
        sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
        ;;
      3 )
        echo 30 | dialog --title "Installing OSP" --gauge "Installing Nginx Core" 10 70 0
        install_nginx_core
        echo 60 | dialog --title "Installing OSP" --gauge "Installing OSP-RTMP" 10 70 0
        install_osp_rtmp
        echo 90 | dialog --title "Installing OSP" --gauge "Restarting Nginx Core" 10 70 0
        sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
        ;;
      4 )
        echo 30 | dialog --title "Installing OSP" --gauge "Installing Nginx Core" 10 70 0
        install_nginx_core
        echo 60 | dialog --title "Installing OSP" --gauge "Installing OSP-EDGE" 10 70 0
        install_osp_edge
        echo 90 | dialog --title "Installing OSP" --gauge "Restarting Nginx Core" 10 70 0
        sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
        ;;
      5 )
        echo 30 | dialog --title "Installing OSP" --gauge "Installing Nginx Core" 10 70 0
        install_nginx_core
        echo 60 | dialog --title "Installing OSP" --gauge "Installing ejabberd" 10 70 0
        install_ejabberd
        echo 90 | dialog --title "Installing OSP" --gauge "Restarting Nginx Core" 10 70 0
        sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
        ;;
    esac
  done
}

upgrade_menu() {
    while true; do
    exec 3>&1
    selection=$(dialog \
      --backtitle "Open Streaming Platform - $VERSION" \
      --title "Menu" \
      --clear \
      --cancel-label "Exit" \
      --menu "Please select:" $HEIGHT $WIDTH 7 \
      "1" "Upgrade OSP - Single Server" \
      "2" "Upgrade OSP-Core" \
      "3" "Upgrade OSP-RTMP" \
      "4" "Upgrade OSP-Edge" \
      "5" "Upgrade eJabberd" \
      "6" "Upgrade DB" \
      2>&1 1>&3)
    exit_status=$?
    exec 3>&-
    case $exit_status in
      $DIALOG_CANCEL)
        clear
        echo "Program terminated."
        exit
        ;;
      $DIALOG_ESC)
        clear
        echo "Program aborted." >&2
        exit 1
        ;;
    esac
    case $selection in
      0 )
        clear
        echo "Program terminated."
        ;;
      1 )
        echo 10 | dialog --title "Upgrade OSP" --gauge "Upgrading OSP Core" 10 70 0
        upgrade_osp
        echo 20 | dialog --title "Upgrade OSP" --gauge "Upgrading OSP-RTMP" 10 70 0
        upgrade_rtmp
        echo 30 | dialog --title "Upgrade OSP" --gauge "Upgrading ejabberd" 10 70 0
        upgrade_ejabberd
        echo 40 | dialog --title "Upgrade OSP" --gauge "Upgrading Database" 10 70 0
        upgrade_db
        echo 50 | dialog --title "Upgrade OSP" --gauge "Restarting ejabberd" 10 70 0
        sudo systemctl restart ejabberd >> $OSPLOG 2>&1
        echo 75 | dialog --title "Upgrade OSP" --gauge "Restarting Nginx Core" 10 70 0
        sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
        echo 85 | dialog --title "Upgrade OSP" --gauge "Restarting OSP Core" 10 70 0
        sudo systemctl restart osp.target >> $OSPLOG 2>&1
        echo 95 | dialog --title "Upgrade OSP" --gauge "Restarting OSP-RTMP" 10 70 0
        sudo systemctl restart osp-rtmp >> $OSPLOG 2>&1
        result=$(echo "OSP - Single Server Upgrade Completed!")
        display_result "Upgrade OSP"
        ;;
      2 )
        echo 10 | dialog --title "Upgrade OSP" --gauge "Upgrading OSP Core" 10 70 0
        upgrade_osp
        echo 40 | dialog --title "Upgrade OSP" --gauge "Upgrading Database" 10 70 0
        upgrade_db
        echo 75 | dialog --title "Upgrade OSP" --gauge "Restarting Nginx Core" 10 70 0
        sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
        echo 85 | dialog --title "Upgrade OSP" --gauge "Restarting OSP Core" 10 70 0
        sudo systemctl restart osp.target >> $OSPLOG 2>&1
        result=$(echo "OSP - Core Upgrade Completed!")
        display_result "Upgrade OSP"
        ;;
      3 )
        echo 20 | dialog --title "Upgrade OSP" --gauge "Upgrading OSP-RTMP" 10 70 0
        upgrade_rtmp
        echo 75 | dialog --title "Upgrade OSP" --gauge "Restarting Nginx Core" 10 70 0
        sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
        echo 95 | dialog --title "Upgrade OSP" --gauge "Restarting OSP-RTMP" 10 70 0
        sudo systemctl restart osp-rtmp >> $OSPLOG 2>&1
        result=$(echo "OSP - RTMP Upgrade Completed!")
        display_result "Upgrade OSP"
        ;;
      4 )
        ;;
      5 )
        echo 30 | dialog --title "Upgrade OSP" --gauge "Upgrading ejabberd" 10 70 0
        upgrade_ejabberd
        echo 50 | dialog --title "Upgrade OSP" --gauge "Restarting ejabberd" 10 70 0
        sudo systemctl restart ejabberd >> $OSPLOG 2>&1
        echo 75 | dialog --title "Upgrade OSP" --gauge "Restarting Nginx Core" 10 70 0
        sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
        result=$(echo "eJabberd Upgrade Completed! You will need to edit /usr/local/ejabberd/conf/auth_osp.py again")
        display_result "Upgrade OSP"
        ;;
      6)
        upgrade_db
        result=$(echo "Database Upgrade Complete")
        display_result "Upgrade OSP"
    esac
  done
}

##########################################################
# Start Main Script Execution
##########################################################
sudo mkdir /var/log/osp/ >> /dev/null
if [ $# -eq 0 ]
  then
    while true; do
      exec 3>&1
      selection=$(dialog \
        --backtitle "Open Streaming Platform - $VERSION" \
        --title "Menu" \
        --clear \
        --cancel-label "Exit" \
        --menu "Please select:" $HEIGHT $WIDTH 7 \
        "1" "Install..." \
        "2" "Upgrade..." \
        "3" "Reset Nginx Configuration" \
        "4" "Reset EJabberD Configuration" \
        2>&1 1>&3)
      exit_status=$?
      exec 3>&-
      case $exit_status in
        $DIALOG_CANCEL)
          clear
          echo "Program terminated."
          exit
          ;;
        $DIALOG_ESC)
          clear
          echo "Program aborted." >&2
          exit 1
          ;;
      esac
      case $selection in
        0 )
          clear
          echo "Program terminated."
          ;;
        1 )
          install_menu
          ;;
        2 )
          upgrade_menu
          ;;
        3 )
          reset_nginx
          result=$(echo "Nginx Configuration has been reset.\n\nBackup of nginx.conf was stored at /usr/local/nginx/conf/nginx.conf.bak")
          display_result "Reset Results"
          ;;
        4 )
          reset_ejabberd
          result=$(echo "EJabberD has been reset and OSP has been restarted")
          display_result "Reset Results"
          ;;
      esac
    done
  else
    case $1 in
      help )
        echo "Available Commands:"
        echo ""
        echo "help: Displays this help"
        echo "install: Installs/Reinstalls OSP Components - Options: osp, osp-core, nginx, rtmp, edge, ejabberd"
        echo "restart: Restarts OSP Components - Options: osp, osp-core, nginx, rtmp, ejabberd"
        echo "upgrade: Upgrades OSP Components - Options: osp, osp-core, rtmp, ejabberd, db"
        echo "reset: Resets OSP Compoents to Defaults - Options: nginx, ejabberd"
        ;;
      install )
        case $2 in
          osp )
            install_nginx_core
            install_redis
            install_ejabberd
            install_osp_rtmp
            install_osp
            sudo cp /opt/osp-rtmp/conf/config.py.dist /opt/osp-rtmp/conf/config.py >> $OSPLOG 2>&1
            sudo cp /opt/osp/conf/config.py.dist /opt/osp/conf/config.py >> $OSPLOG 2>&1
            generate_ejabberd_admin
            install_mysql
            sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
            sudo systemctl start osp.target >> $OSPLOG 2>&1
            sudo systemctl start osp-rtmp >> $OSPLOG 2>&1
            ;;
          nginx )
            install_nginx_core >> $OSPLOG 2>&1
            ;;
          rtmp )
            install_nginx_core >> $OSPLOG 2>&1
            install_osp_rtmp >> $OSPLOG 2>&1
            ;;
          edge )
            install_nginx_core >> $OSPLOG 2>&1
            install_osp_edge >> $OSPLOG 2>&1
            ;;
          ejabberd )
            install_nginx_core >> $OSPLOG 2>&1
            install_ejabberd >> $OSPLOG 2>&1
            ;;
          osp-core )
            install_nginx_core >> $OSPLOG 2>&1
            install_osp >> $OSPLOG 2>&1
            ;;
        esac
        ;;
      restart )
        case $2 in
          osp )
            sudo systemctl restart ejabberd >> $OSPLOG 2>&1
            sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
            sudo systemctl restart osp-rtmp >> $OSPLOG 2>&1
            sudo systemctl restart osp.target >> $OSPLOG 2>&1
            ;;
          osp-core )
            sudo systemctl restart osp.target >> $OSPLOG 2>&1
            ;;
          nginx )
            sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
            ;;
          rtmp )
            sudo systemctl restart osp-rtmp >> $OSPLOG 2>&1
            ;;
          ejabberd )
            sudo systemctl restart ejabberd >> $OSPLOG 2>&1
            ;;
        esac
        ;;
      upgrade )
        case $2 in
          osp )
            upgrade_osp
            upgrade_rtmp
            upgrade_ejabberd
            upgrade_db
            sudo systemctl restart ejabberd >> $OSPLOG 2>&1
            sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
            sudo systemctl restart osp.target >> $OSPLOG 2>&1
            sudo systemctl restart osp-rtmp >> $OSPLOG 2>&1
            ;;
          osp-core )
            upgrade_osp
            sudo systemctl restart osp.target >> $OSPLOG 2>&1
            ;;
          rtmp )
            upgrade_rtmp
            ;;
          ejabberd )
            upgrade_ejabberd
            ;;
          db )
            upgrade_db
            ;;
        esac
        ;;
      reset )
        case $2 in
          nginx )
            reset_nginx
            ;;
          ejabberd )
            reset_ejabberd
            ;;
          esac
          ;;
      esac
    fi

#######################################################
# End
#######################################################