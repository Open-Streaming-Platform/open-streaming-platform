#!/bin/bash
# OSP Control Script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OSPLOG="/var/log/osp/installer.log"
VERSION=$(<version)

NGINX_BUILD_VERSION="1.25.2"
NGINX_RTMP_VERSION="1.2.11"
NGINX_ZLIB_VERSION="1.3"
EJABBERD_VERSION="23.04"

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

config_smtp() {
  smtpSendAs=""
  smtpServerAddress=""
  smtpServerPort=""
  smtpUsername=""
  smtpPassword=""
  smtpEncryption=""
exec 3>&1
  # Store data to $VALUES variable
while [[ -z $smtpSendAs || -z $smtpServerAddress || -z $smtpServerPort ]];
do   
  dialog --separate-widget $'\n' --ok-label "Save" \
            --title "Configure SMTP Settings" \
            --form "Please Configure your SMTP Settings (Required)" \
  20 70 0 \
          "Send Email As:"          1 1   "$smtpSendAs"           1 25 40 0 \
          "SMTP Server Address:"    2 1   "$smtpServerAddress"    2 25 40 0 \
          "SMTP Server Port:"       3 1   "$smtpServerPort"           3 25 5 0 \
          "Username:"               4 1   "$smtpUsername"               4 25 40 0 \
          "Password:"               5 1   "$smtpPassword"               5 25 40 0 \
  2>&1 1>&3 | {
    read -r smtpSendAs
    read -r smtpServerAddress
    read -r smtpServerPort
    read -r smtpUsername
    read -r smtpPassword
  }
done
cmd=(dialog --title "Configure SMTP Settings" --radiolist "Select SMTP Server Encryption": 20 70 0 1 "None" on  2 "TLS" off 3 "SSL" off
)

choice=$("${cmd[@]}" "${options[@]}" 2>&1 > /dev/tty )
smtpEncryption=""
case choice in

  1)
    smtpEncryption="none"
    ;;

  2)
    smtpEncryption="tls"
    ;;

  3)
    smtpEncryption="ssl"
    ;;

  *)
    smtpEncryption="none"
    ;;
esac
sudo sed -i "s/sendAs@email.com/$smtpSendAs/" /opt/osp/conf/config.py >> $OSPLOG 2>&1
sudo sed -i "s/smtp.email.com/$smtpServerAddress/" /opt/osp/conf/config.py >> $OSPLOG 2>&1
sudo sed -i "s/smtpServerPort=25/smtpServerPort=$smtpServerPort/" /opt/osp/conf/config.py >> $OSPLOG 2>&1
sudo sed -i "s/smtpUsername=\"\"/smtpUsername=\"$smtpUsername\"/" /opt/osp/conf/config.py >> $OSPLOG 2>&1
sudo sed -i "s/smtpPassword=\"\"/smtpPassword=\"$smtpPassword\"/" /opt/osp/conf/config.py >> $OSPLOG 2>&1
sudo sed -i "s/smtpEncryption=\"none\"/smtpEncryption=\"$smtpEncryption\"/" /opt/osp/conf/config.py >> $OSPLOG 2>&1


exec 3>&-

}

reset_nginx() {
  if cd /usr/local/nginx/conf
  then
    echo 5 | dialog --title "Reset Nginx Configuration" --gauge "Stopping Nginx-OSP" 10 70 0
    sudo systemctl stop nginx-osp
    sudo systemctl disable nginx-osp
    echo 20 | dialog --title "Reset Nginx Configuration" --gauge "Backing up Existing Conf" 10 70 0
    sudo mkdir /tmp/nginxbak >> $OSPLOG 2>&1
    sudo cp -R /usr/local/nginx/conf /tmp/nginxbak >> $OSPLOG 2>&1
    cd /
    echo 30 | dialog --title "Reset Nginx Configuration" --gauge "Removing Previous Nginx Instance" 10 70 0
    sudo rm -rf /usr/local/nginx >> $OSPLOG 2>&1
    echo 50 | dialog --title "Reset Nginx Configuration" --gauge "Rebuilding Nginx from Source" 10 70 0
    install_nginx_core
    echo 75 | dialog --title "Reset Nginx Configuration" --gauge "Restoring Nginx Conf" 10 70 0
    sudo cp -R /tmp/nginxbak/conf/* /usr/local/nginx/conf/ >> $OSPLOG 2>&1
    echo 90 | dialog --title "Reset Nginx Configuration" --gauge "Restarting Nginx-OSP" 10 70 0
    sudo systemctl stop nginx-osp
    sudo systemctl start nginx-osp
  fi
}

reset_ejabberd() {
  echo 5 | dialog --title "Reset eJabberd Configuration" --gauge "Stopping eJabberd" 10 70 0
  sudo systemctl stop ejabberd >> $OSPLOG 2>&1
  echo 10 | dialog --title "Reset eJabberd Configuration" --gauge "Removing eJabberd" 10 70 0
  sudo rm -rf /usr/local/ejabberd >> $OSPLOG 2>&1
  sudo rm -rf /opt/ejabberd >> $OSPLOG 2>&1
  echo 20 | dialog --title "Reset eJabberd Configuration" --gauge "Downloading eJabberd" 10 70 0
  sudo wget -O "/tmp/ejabberd-$EJABBERD_VERSION-linux-x64.run" "https://www.process-one.net/downloads/downloads-action.php?file=/$EJABBERD_VERSION/ejabberd-$EJABBERD_VERSION-1-linux-x64.run" >> $OSPLOG 2>&1
  sudo chmod +x /tmp/ejabberd-$EJABBERD_VERSION-linux-x64.run >> $OSPLOG 2>&1
  echo 30 | dialog --title "Reset eJabberd Configuration" --gauge "Reinstalling eJabberd" 10 70 0
  sudo yes | /tmp/ejabberd-$EJABBERD_VERSION-linux-x64.run --quiet >> $OSPLOG 2>&1
  sudo ln -s /opt/ejabberd /usr/local/ejabberd >> $OSPLOG 2>&1
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
  sudo mkdir /opt/ejabberd/conf >> $OSPLOG 2>&1
  sudo cp /opt/osp/installs/ejabberd/setup/ejabberd.yml /opt/ejabberd/conf/ejabberd.yml >> $OSPLOG 2>&1
  sudo cp /opt/osp/installs/ejabberd/setup/inetrc /opt/ejabberd/conf/inetrc >> $OSPLOG 2>&1
  sudo cp /opt/osp/installs/ejabberd/setup/auth_osp.py /opt/ejabberd/conf/auth_osp.py >> $OSPLOG 2>&1
  sudo cp /opt/ejabberd/bin/ejabberd.service /etc/systemd/system/ejabberd.service >> $OSPLOG 2>&1
  user_input=$(\
  dialog --nocancel --title "Setting up eJabberd" \
         --inputbox "Enter your Site Address (Must match FQDN without http):" 8 80 \
  3>&1 1>&2 2>&3 3>&-)
  echo 80 | dialog --title "Reset eJabberd Configuration" --gauge "Updating eJabberd Config File" 10 70 0
  sudo sed -i "s/CHANGEME/$user_input/g" /opt/ejabberd/conf/ejabberd.yml >> $OSPLOG 2>&1
  echo 85 | dialog --title "Reset eJabberd Configuration" --gauge "Restarting eJabberd" 10 70 0
  sudo systemctl daemon-reload >> $OSPLOG 2>&1
  sudo systemctl enable ejabberd >> $OSPLOG 2>&1
  sudo systemctl start ejabberd >> $OSPLOG 2>&1
  echo 90 | dialog --title "Reset eJabberd Configuration" --gauge "Setting eJabberd Local Admin" 10 70 0
  sudo /opt/ejabberd-$EJABBERD_VERSION/bin/ejabberdctl register admin localhost $ADMINPASS >> $OSPLOG 2>&1
  sudo /opt/ejabberd-$EJABBERD_VERSION/bin/ejabberdctl change_password admin localhost $ADMINPASS >> $OSPLOG 2>&1
  echo 95 | dialog --title "Reset eJabberd Configuration" --gauge "Restarting OSP" 10 70 0
  sudo systemctl restart osp.target >> $OSPLOG 2>&1
}

upgrade_db() {
  UPGRADELOG="/opt/osp/logs/upgrade.log"
  echo 0 | dialog --title "Upgrading Database" --gauge "Stopping OSP" 10 70 0
  sudo systemctl stop osp.target >> $OSPLOG 2>&1
  cd /opt/osp
  echo 50 | dialog --title "Upgrading Database" --gauge "Upgrading Database" 10 70 0
  flask db upgrade >> $OSPLOG 2>&1
  echo 75 | dialog --title "Upgrading Database" --gauge "Starting OSP" 10 70 0
  sudo systemctl start osp.target >> $OSPLOG 2>&1
  echo 100 | dialog --title "Upgrading Database" --gauge "Complete" 10 70 0
  cd $DIR
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
  #sudo add-apt-repository ppa:jonathonf/ffmpeg-4 -y >> $OSPLOG 2>&1
  #echo 75 | dialog --title "Installing FFMPEG" --gauge "Installing FFMPEG" 10 70 0
  sudo apt-get update >> $OSPLOG 2>&1
  echo 90 | dialog --title "Installing FFMPEG" --gauge "Installing FFMPEG" 10 70 0
  sudo apt-get install ffmpeg -y >> $OSPLOG 2>&1
}

install_mysql(){
  SQLPASS=$( cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1 )
  echo 10 | dialog --title "Installing MySQL" --gauge "Installing MySQL Server" 10 70 0
  sudo apt-get install mariadb-server -y >> $OSPLOG 2>&1
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
          sudo wget -q "http://nginx.org/download/nginx-$NGINX_BUILD_VERSION.tar.gz" >> $OSPLOG 2>&1
          echo 15 | dialog --title "Installing Nginx-Core" --gauge "Downloading Required Modules" 10 70 0
          #sudo wget -q "https://github.com/arut/nginx-rtmp-module/archive/v$NGINX_RTMP_VERSION.zip" >> $OSPLOG 2>&1
          sudo wget -q "https://github.com/winshining/nginx-http-flv-module/archive/refs/tags/v$NGINX_RTMP_VERSION.tar.gz" >> $OSPLOG 2>&1
          echo 20 | dialog --title "Installing Nginx-Core" --gauge "Downloading Required Modules" 10 70 0
          sudo wget -q "http://www.zlib.net/zlib-$NGINX_ZLIB_VERSION.tar.gz" >> $OSPLOG 2>&1
          echo 25 | dialog --title "Installing Nginx-Core" --gauge "Downloading Required Modules" 10 70 0
          sudo wget -q "https://bitbucket.org/nginx-goodies/nginx-sticky-module-ng/get/master.tar.gz" >> $OSPLOG 2>&1
          echo 30 | dialog --title "Installing Nginx-Core" --gauge "Decompressing Nginx Source and Modules" 10 70 0
          sudo tar xfz nginx-$NGINX_BUILD_VERSION.tar.gz >> $OSPLOG 2>&1
          #sudo unzip -qq -o v$NGINX_RTMP_VERSION.zip >> $OSPLOG 2>&1
          sudo tar xfz v$NGINX_RTMP_VERSION.tar.gz >> $OSPLOG 2>&1
          sudo tar xfz zlib-$NGINX_ZLIB_VERSION.tar.gz >> $OSPLOG 2>&1
          sudo tar xfz master.tar.gz >> $OSPLOG 2>&1

          # Apply Any Precompile Nginx-RTMP Patches
          echo 31 | dialog --title "Installing Nginx-Core" --gauge "Applying Precompile Patches" 10 70 0
          if cd nginx-http-flv-module-$NGINX_RTMP_VERSION
          then
            sudo cp $DIR/installs/nginx-core/patches/mr-1158/1158.patch /tmp/nginx-http-flv-module-$NGINX_RTMP_VERSION/1158.patch >> $OSPLOG 2>&1
            sudo patch -s -p 1 < 1158.patch
            cd ..
          else
              echo "Unable to Access Nginx-RTMP Module Source"
              exit 1
          fi

          echo 35 | dialog --title "Installing Nginx-Core" --gauge "Building Nginx from Source" 10 70 0
          if cd nginx-$NGINX_BUILD_VERSION
          then
                  ./configure --with-http_ssl_module --with-http_v2_module --with-http_auth_request_module --with-http_stub_status_module --add-module=../nginx-http-flv-module-$NGINX_RTMP_VERSION --add-module=../nginx-goodies-nginx-sticky-module-ng-08a395c66e42 --with-zlib=../zlib-$NGINX_ZLIB_VERSION --with-cc-opt="-Wimplicit-fallthrough=0" >> $OSPLOG 2>&1
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
  sudo mkdir /usr/local/nginx/conf/custom >> $OSPLOG 2>&1

  sudo cp $DIR/installs/nginx-core/osp-custom-servers.conf /usr/local/nginx/conf/custom/ >> $OSPLOG 2>&1
  sudo cp $DIR/installs/nginx-core/osp-custom-serversredirect.conf /usr/local/nginx/conf/custom/ >> $OSPLOG 2>&1

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
  sudo mkdir -p "$web_root/keys" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/keys-adapt" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/pending" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/ingest" >> $OSPLOG 2>&1

  s3DriveMount=$(mount | grep -iE "/var/www/videos" | grep s3fs | wc -l)
  if test $s3DriveMount -eq 0
  then
    echo 90 | dialog --title "Installing Nginx-Core" --gauge "Setting Ownership of OSP Video Directories" 10 70 0
    sudo chown -R "$http_user:$http_user" "$web_root" >> $OSPLOG 2>&1
  fi
  # Start Nginx
  echo 100 | dialog --title "Installing Nginx-Core" --gauge "Starting Nginx" 10 70 0
  sudo systemctl start nginx-osp.service >> $OSPLOG 2>&1

}

install_osp_rtmp() {
  echo 10 | dialog --title "Installing OSP-RTMP" --gauge "Intalling Prereqs" 10 70 0
  install_prereq
  echo 25 | dialog --title "Installing OSP-RTMP" --gauge "Installing Requirements.txt" 10 70 0
  sudo pip3 uninstall -r $DIR/installs/osp-rtmp/setup/remove_requirements.txt -y >> $OSPLOG 2>&1
  sudo pip3 install -r $DIR/installs/osp-rtmp/setup/requirements.txt >> $OSPLOG 2>&1

  echo 40 | dialog --title "Installing OSP-RTMP" --gauge "Setting Up Nginx Configs" 10 70 0
  sudo cp $DIR/installs/osp-rtmp/setup/nginx/servers/*.conf /usr/local/nginx/conf/servers >> $OSPLOG 2>&1
  sudo cp $DIR/installs/osp-rtmp/setup/nginx/services/*.conf /usr/local/nginx/conf/services >> $OSPLOG 2>&1
  sudo cp $DIR/installs/osp-rtmp/setup/nginx/custom/osp-rtmp-* /usr/local/nginx/conf/custom >> $OSPLOG 2>&1

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

install_osp_proxy() {
  user_input=$(\
  dialog --nocancel --title "Setting up OSP-Proxy" \
         --inputbox "Enter your OSP-Core Protocol and FQDN (ex:https://osp.example.com):" 8 80 \
  3>&1 1>&2 2>&3 3>&-)
  # Grab Configuration
  echo 10 | dialog --title "Installing OSP-Proxy" --gauge "Installing Configuration Files" 10 70 0
  sudo cp $DIR/installs/osp-proxy/setup/nginx/locations/osp-proxy-locations.conf /usr/local/nginx/conf/locations >> $OSPLOG 2>&1
  sudo cp $DIR/installs/osp-proxy/setup/nginx/servers/osp-proxy-servers.conf /usr/local/nginx/conf/servers >> $OSPLOG 2>&1
  sudo cp $DIR/installs/osp-proxy/setup/nginx/nginx.conf /usr/local/nginx/conf/nginx.conf >> $OSPLOG 2>&1
  sudo cp $DIR/installs/osp-proxy/setup/nginx/cors.conf /usr/local/nginx/conf/cors.conf >> $OSPLOG 2>&1
  sudo cp $DIR/installs/osp-proxy/setup/nginx/custom/osp-proxy-custom* /usr/local/nginx/conf/custom/ >> $OSPLOG 2>&1

  # Setup OSP Proxy Directory
  echo 25 | dialog --title "Installing OSP-Proxy" --gauge "Installing OSP-Proxy Application Prereqs" 10 70 0
  sudo pip3 install -r $DIR/installs/osp-proxy/setup/requirements.txt >> $OSPLOG 2>&1

  # Install OSP Proxy
  echo 50 | dialog --title "Installing OSP-Proxy" --gauge "Installing OSP-Proxy Application Prereqs" 10 70 0
  sudo mkdir /opt/osp-proxy >> $OSPLOG 2>&1
  sudo cp -R $DIR/installs/osp-proxy/* /opt/osp-proxy >> $OSPLOG 2>&1
  sudo cp /opt/osp-proxy/conf/config.py.dist /opt/osp-proxy/conf/config.py >> $OSPLOG 2>&1
  sudo chmod +x /opt/osp-proxy/updateUpstream.sh >> $OSPLOG 2>&1
  sudo mkdir -p /var/cache/nginx/osp_cache_temp >> $OSPLOG 2>&1

  # Setup Configuration with IP
  echo 75 | dialog --title "Installing OSP-Proxy" --gauge "Installing Configuration Files" 10 70 0
  sed -i "s|#CHANGEMETOOSPCORE|$user_input|g" /opt/osp-proxy/conf/config.py >> $OSPLOG 2>&1

  # Setup Install OSP-Proxy Service
  echo 85 | dialog --title "Installing OSP-Proxy" --gauge "Installing Configuration Files" 10 70 0
  sudo cp $DIR/installs/osp-proxy/setup/gunicorn/osp-proxy.service /etc/systemd/system/osp-proxy.service >> $OSPLOG 2>&1
  sudo systemctl daemon-reload >> $OSPLOG 2>&1
  sudo systemctl enable osp-proxy.service >> $OSPLOG 2>&1
  sudo systemctl start osp-proxy.service >> $OSPLOG 2>&1

  # Enable OSP Upstream Updater
  echo 90 | dialog --title "Installing OSP-Proxy" --gauge "Installing OSP-Proxy Upstream Updater" 10 70 0
  cronjob="*/5 * * * * /opt/osp-proxy/updateUpstream.sh"
  (sudo crontab -u root -l;sudo echo "$cronjob" ) | sudo crontab -u root -
  sudo systemctl restart cron >> $OSPLOG 2>&1

}

install_osp_edge () {

  user_input=$(\
  dialog --nocancel --title "Setting up OSP-Edge" \
         --inputbox "Enter your OSP-RTMP IP Address. Use Commas to Separate Multiple Values (ex: 192.168.0.4,192.168.8.5):" 8 80 \
  3>&1 1>&2 2>&3 3>&-)

  IFS="," read -a rtmpArray <<< $user_input
  rtmpString=""
  for i in "${rtmpArray[@]}"
  do
        rtmpString+="allow publish $i;\n"
  done

  core_input=$(\
  dialog --nocancel --title "Setting up OSP-Edge" \
         --inputbox "Enter your OSP-Core IP Address. Use Commas to Separate Multiple Values (ex: 192.168.0.4,192.168.8.5):" 8 80 \
  3>&1 1>&2 2>&3 3>&-)

  IFS="," read -a coreArray <<< $core_input
  coreString=""
  for i in "${coreArray[@]}"
  do
        coreString+="allow $i;\n"
  done

  # Grab Configuration
  echo 10 | dialog --title "Installing OSP-Edge" --gauge "Installing Configuration Files" 10 70 0
  sudo cp $DIR/installs/osp-edge/setup/nginx/locations/osp-edge-redirects.conf /usr/local/nginx/conf/locations >> $OSPLOG 2>&1
  sudo cp $DIR/installs/osp-edge/setup/nginx/servers/osp-edge-servers.conf /usr/local/nginx/conf/servers >> $OSPLOG 2>&1
  sudo cp $DIR/installs/osp-edge/setup/nginx/services/osp-edge-rtmp.conf /usr/local/nginx/conf/services >> $OSPLOG 2>&1
  sudo cp $DIR/installs/osp-edge/setup/nginx/custom/osp-edge-custom* /usr/local/nginx/conf/custom >> $OSPLOG 2>&1

  # Setup Configuration with IP
  echo 40 | dialog --title "Installing OSP-Edge" --gauge "Installing Configuration Files" 10 70 0
  sed -i "s/#ALLOWRTMP/$rtmpString/g" /usr/local/nginx/conf/custom/osp-edge-custom-allowedpub.conf >> $OSPLOG 2>&1
  sed -i "s/#ALLOWCORE/$coreString/g" /usr/local/nginx/conf/custom/osp-edge-custom-nginxstat.conf >> $OSPLOG 2>&1

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
  sudo wget -O "/tmp/ejabberd-$EJABBERD_VERSION-linux-x64.run" "https://www.process-one.net/downloads/downloads-action.php?file=/$EJABBERD_VERSION/ejabberd-$EJABBERD_VERSION-1-linux-x64.run" >> $OSPLOG 2>&1
  echo 20 | dialog --title "Installing ejabberd" --gauge "Installing ejabberd" 10 70 0
  sudo chmod +x /tmp/ejabberd-$EJABBERD_VERSION-linux-x64.run >> $OSPLOG 2>&1
  sudo yes | /tmp/ejabberd-$EJABBERD_VERSION-linux-x64.run --quiet >> $OSPLOG 2>&1
  sudo ln -s /opt/ejabberd /usr/local/ejabberd >> $OSPLOG 2>&1
  echo 35 | dialog --title "Installing ejabberd" --gauge "Installing Configuration Files" 10 70 0
  mkdir /opt/ejabberd/conf >> $OSPLOG 2>&1
  sudo cp $DIR/installs/ejabberd/setup/ejabberd.yml /opt/ejabberd/conf/ejabberd.yml >> $OSPLOG 2>&1
  sudo cp $DIR/installs/ejabberd/setup/auth_osp.py /opt/ejabberd/conf/auth_osp.py >> $OSPLOG 2>&1cd
  sudo cp $DIR/installs/ejabberd/setup/inetrc /opt/ejabberd/conf/inetrc >> $OSPLOG 2>&1
  sudo cp /opt/ejabberd-$EJABBERD_VERSION/bin/ejabberd.service /etc/systemd/system/ejabberd.service >> $OSPLOG 2>&1
  # If we don't have the site address, prompt the user
  if [ -z "$OSP_EJABBERD_SITE_ADDRESS" ]; then
    user_input=$(\
    dialog --nocancel --title "Setting up eJabberd" \
           --inputbox "Enter your Site Address (Must match FQDN without http):" 8 80 \
    3>&1 1>&2 2>&3 3>&-)
  else
    user_input="$OSP_EJABBERD_SITE_ADDRESS"
  fi
  echo 65 | dialog --title "Installing ejabberd" --gauge "Setting Up ejabberd Configuration" 10 70 0
  sudo sed -i "s/CHANGEME/$user_input/g" /opt/ejabberd/conf/ejabberd.yml >> $OSPLOG 2>&1
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
  sudo sed -i "s/CHANGEME/$user_input/g" /opt/ejabberd/conf/ejabberd.yml >> $OSPLOG 2>&1
  sudo /opt/ejabberd-$EJABBERD_VERSION/bin/ejabberdctl register admin localhost $ADMINPASS >> $OSPLOG 2>&1
  sudo /opt/ejabberd-$EJABBERD_VERSION/bin/ejabberdctl change_password admin localhost $ADMINPASS >> $OSPLOG 2>&1
  sudo systemctl restart ejabberd
}

install_osp() {
  cwd=$PWD

  echo "Starting OSP Install" >> $OSPLOG 2>&1
  echo 0 | dialog --title "Installing OSP" --gauge "Installing Linux Dependencies" 10 70 0

  install_prereq
  sudo pip3 uninstall -r $DIR/setup/remove_requirements.txt -y >> $OSPLOG 2>&1
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
  sudo cp $DIR/setup/nginx/upstream/osp.conf /usr/local/nginx/conf/upstream >> $OSPLOG 2>&1
  sudo cp $DIR/setup/nginx/upstream/osp-edge.conf /usr/local/nginx/conf/upstream >> $OSPLOG 2>&1

  # Create HLS directory
  echo 60 | dialog --title "Installing OSP" --gauge "Creating OSP Video Directories" 10 70 0
  sudo mkdir -p "$web_root" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/live" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/videos" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/images" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/images/stickers" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/live-adapt" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/stream-thumb" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/keys" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/keys-adapt" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/pending" >> $OSPLOG 2>&1
  sudo mkdir -p "$web_root/ingest" >> $OSPLOG 2>&1

  s3DriveMount=$(mount | grep -iE "/var/www/videos" | grep s3fs | wc -l)
  if test $s3DriveMount -eq 0
  then
    echo 70 | dialog --title "Installing OSP" --gauge "Setting Ownership of OSP Video Directories" 10 70 0
    sudo chown -R "$http_user:$http_user" "$web_root" >> $OSPLOG 2>&1
  fi

  sudo chown -R "$http_user:$http_user" /opt/osp >> $OSPLOG 2>&1
  sudo chown -R "$http_user:$http_user" /opt/osp/.git >> $OSPLOG 2>&1

  # Copy Initial Favicons
  sudo cp $DIR/static/android-chrome-192x192.png $web_root/images/ >> $OSPLOG 2>&1
  sudo cp $DIR/static/android-chrome-512x512.png $web_root/images/ >> $OSPLOG 2>&1
  sudo cp $DIR/static/apple-touch-icon.png $web_root/images/ >> $OSPLOG 2>&1
  sudo cp $DIR/static/favicon.ico $web_root/images/ >> $OSPLOG 2>&1
  sudo cp $DIR/static/favicon-16x16.png $web_root/images/ >> $OSPLOG 2>&1
  sudo cp $DIR/static/favicon-32x32.png  $web_root/images/ >> $OSPLOG 2>&1

  install_celery

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

install_celery() {
  # Setup Celery
  echo 50 | dialog --title "Installing OSP" --gauge "Setting Up Celery" 10 70 0
  sudo mkdir /var/log/celery >> $OSPLOG 2>&1
  sudo chown -R www-data:www-data /var/log/celery >> $OSPLOG 2>&1
  sudo cp -rf $DIR/setup/celery/osp-celery.service /etc/systemd/system >> $OSPLOG 2>&1
  sudo cp -rf $DIR/setup/celery/celery /etc/default/celery >> $OSPLOG 2>&1
  sudo systemctl daemon-reload >> $OSPLOG 2>&1
  sudo systemctl enable osp-celery >> $OSPLOG 2>&1
}

install_celery_beat() {
  echo 50 | dialog --title "Installing OSP" --gauge "Setting Up Celery Beat" 10 70 0
  sudo cp -rf $DIR/setup/celery/osp-celery-beat.service /etc/systemd/system >> $OSPLOG 2>&1
  sudo systemctl daemon-reload >> $OSPLOG 2>&1
  sudo systemctl enable osp-celery-beat >> $OSPLOG 2>&1
}

install_celery_flower() {
  echo 50 | dialog --title "Installing OSP" --gauge "Setting Up Celery Flower" 10 70 0
  sudo pip3 install flower >> $OSPLOG 2>&1
  sudo cp -rf $DIR/setup/celery/osp-celery-flower.service /etc/systemd/system >> $OSPLOG 2>&1
  sudo cp -rf $DIR/setup/celery/celery-flower /etc/default/celery-flower >> $OSPLOG 2>&1
  ADMINPASS=$( cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 16 | head -n 1 )
  sed -i "s/CHANGEME/$ADMINPASS/" /etc/default/celery-flower >> $OSPLOG 2>&1
  sudo systemctl daemon-reload >> $OSPLOG 2>&1
  sudo systemctl enable osp-celery-flower >> $OSPLOG 2>&1
  result=$(echo "OSP-Celery-Flower Install Completed! \n\nVisit http://FQDN:5572 to configure\n\nUsername: Admin \nPassword: $ADMINPASS \n\nYou can change the password by editing the /etc/default/celery-flower file")
        display_result "Install OSP-Celery-Flower"
}

upgrade_celery() {
  install_celery
  sudo systemctl restart osp-celery >> $OSPLOG 2>&1
}

upgrade_celery_beat() {
  install_celery_beat
  sudo systemctl restart osp-celery-beat >> $OSPLOG 2>&1
}

upgrade_osp() {
   UPGRADELOG="/opt/osp/logs/upgrade.log"
   if cd /opt/osp
   then
     echo 0 | dialog --title "Upgrading OSP" --gauge "Pulling Git Repo" 10 70 0
     echo 10 | dialog --title "Upgrading OSP" --gauge "Setting /opt/osp Ownership" 10 70 0
     sudo chown -R $http_user:$http_user /opt/osp >> $UPGRADELOG 2>&1
     echo 25 | dialog --title "Upgrading OSP" --gauge "Stopping OSP" 10 70 0
     sudo systemctl stop osp.target >> $UPGRADELOG 2>&1
     echo 30 | dialog --title "Upgrading OSP" --gauge "Stopping Nginx" 10 70 0
     sudo systemctl stop nginx-osp >> $UPGRADELOG 2>&1
     echo 35 | dialog --title "Upgrading OSP" --gauge "Installing Python Dependencies" 10 70 0
     sudo pip3 uninstall -r /opt/osp/setup/remove_requirements.txt -y >> $UPGRADELOG 2>&1
     sudo pip3 install -r /opt/osp/setup/requirements.txt >> $UPGRADELOG 2>&1
     echo 45 | dialog --title "Upgrading OSP" --gauge "Upgrading Nginx-RTMP Configurations" 10 70 0
     sudo cp -rf /opt/osp/setup/nginx/locations/* /usr/local/nginx/conf/locations >> $OSPLOG 2>&1
     sudo cp -rf /opt/osp/setup/nginx/upstream/osp.conf /usr/local/nginx/conf/upstream >> $OSPLOG 2>&1
     sudo cp -rf /opt/osp/setup/nginx/upstream/osp-edge.conf /usr/local/nginx/conf/upstream >> $OSPLOG 2>&1
     echo 50 | dialog --title "Upgrading OSP" --gauge "Upgrading Database" 10 70 0
     echo 65 | dialog --title "Upgrading OSP" --gauge "Upgrading Database" 10 70 0
     flask db upgrade >> $UPGRADELOG 2>&1
     echo 75 | dialog --title "Upgrading OSP" --gauge "Starting OSP" 10 70 0
     sudo systemctl start osp.target >> $UPGRADELOG 2>&1
     echo 90 | dialog --title "Upgrading OSP" --gauge "Starting Nginx" 10 70 0
     sudo systemctl start nginx-osp >> $UPGRADELOG 2>&1
     echo 100 | dialog --title "Upgrading OSP" --gauge "Complete" 10 70 0
   else
    echo "Error: /opt/osp Does not Exist" >> $OSPLOG 2>&1
   fi
}

upgrade_proxy() {
  sudo pip3 install -r $DIR/installs/osp-proxy/setup/requirements.txt >> $OSPLOG 2>&1
  sudo cp $DIR/installs/osp-proxy/setup/nginx/locations/*.conf /usr/local/nginx/conf/locations >> $OSPLOG 2>&1
  sudo cp $DIR/installs/osp-proxy/setup/nginx/servers/*.conf /usr/local/nginx/conf/servers >> $OSPLOG 2>&1
  sudo cp $DIR/installs/osp-proxy/setup/nginx/nginx.conf /usr/local/nginx/conf/nginx.conf >> $OSPLOG 2>&1
  sudo cp -R $DIR/installs/osp-proxy/* /opt/osp-proxy >> $OSPLOG 2>&1
}

upgrade_rtmp() {
  sudo pip3 uninstall -r $DIR/installs/osp-rtmp/setup/remove_requirements.txt -y >> $OSPLOG 2>&1
  sudo pip3 install -r $DIR/installs/osp-rtmp/setup/requirements.txt >> $OSPLOG 2>&1
  sudo cp -rf $DIR/installs/osp-rtmp/setup/nginx/servers/*.conf /usr/local/nginx/conf/servers >> $OSPLOG 2>&1
  sudo cp -rf $DIR/installs/osp-rtmp/setup/nginx/services/*.conf /usr/local/nginx/conf/services >> $OSPLOG 2>&1
  sudo cp -R $DIR/installs/osp-rtmp/* /opt/osp-rtmp >> $OSPLOG 2>&1
}

upgrade_ejabberd() {
  sudo cp -rf $DIR/installs/ejabberd/setup/auth_osp.py /opt/ejabberd/conf/auth_osp.py >> $OSPLOG 2>&1
  sudo cp -rf $DIR/installs/ejabberd/setup/nginx/locations/ejabberd.conf /usr/local/nginx/conf/locations/ >> $OSPLOG 2>&1
}

upgrade_edge() {
  sudo cp -rf $DIR/installs/osp-edge/setup/nginx/services/osp-edge-rtmp.conf /usr/local/nginx/conf/services/ >> $OSPLOG 2>&1
  sudo cp -rf $DIR/installs/osp-edge/setup/nginx/locations/osp-edge-redirects.conf /usr/local/nginx/conf/locations/ >> $OSPLOG 2>&1
  sudo cp -rf $DIR/installs/osp-edge/setup/nginx/servers/osp-edge-servers.conf /usr/local/nginx/conf/servers/ >> $OSPLOG 2>&1
}

upgrade_nginxcore() {
  sudo cp -rf $DIR/installs/nginx-core/nginx.conf /usr/local/nginx/conf >> $OSPLOG 2>&1
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
      "5" "Install OSP-Proxy" \
      "6" "Install eJabberd" \
      "7" "Install Celery Beat" \
      "8" "Install Celery Flower" \
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
        config_smtp
        echo 70 | dialog --title "Installing OSP" --gauge "Setting up Celery" 10 70 0
        install_celery
        install_celery_beat
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
        echo 95 | dialog --title "Installing OSP" --gauge "Starting Celery" 10 70 0
        sudo systemctl start osp-celery >> $OSPLOG 2>&1
        sudo systemctl start osp-celery-beat >> $OSPLOG 2>&1
        result=$(echo "OSP Install Completed! \n\nVisit http://FQDN to configure\n\nInstall Log can be found at /opt/osp/logs/install.log")
        display_result "Install OSP"
        ;;
      2 )
        echo 30 | dialog --title "Installing OSP" --gauge "Installing Nginx Core" 10 70 0
        install_nginx_core
        echo 60 | dialog --title "Installing OSP" --gauge "Installing OSP Core" 10 70 0
        install_osp
        echo 70 | dialog --title "Installing OSP" --gauge "Setting Celery" 10 70 0
        install_celery
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
        echo 45 | dialog --title "Installing OSP" --gauge "Installing Redis" 10 70 0
        install_redis
        echo 60 | dialog --title "Installing OSP" --gauge "Installing OSP-Proxy" 10 70 0
        install_osp_proxy
        echo 90 | dialog --title "Installing OSP" --gauge "Restarting Nginx Core" 10 70 0
        sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
        ;;
      6 )
        echo 30 | dialog --title "Installing OSP" --gauge "Installing Nginx Core" 10 70 0
        install_nginx_core
        echo 60 | dialog --title "Installing OSP" --gauge "Installing ejabberd" 10 70 0
        install_ejabberd
        echo 90 | dialog --title "Installing OSP" --gauge "Restarting Nginx Core" 10 70 0
        sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
        ;;
      7 )
        echo 50 | dialog --title "Installing OSP" --gauge "Setting up Celery Beat"
        install_celery_beat
        echo 75 | dialog --title "Installing OSP" --gauge "Starting Celery Beat" 10 70 0
        sudo systemctl start osp-celery
        sudo systemctl start osp-celery-beat
        ;;
      8 )
        echo 50 | dialog --title "Installing OSP" --gauge "Setting up Celery Flower"
        install_celery_flower
        echo 75 | dialog --title "Installing OSP" --gauge "Starting Celery Flower" 10 70 0
        sudo systemctl start osp-celery
        sudo systemctl start osp-celery-beat
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
      "5" "Upgrade OSP-Proxy" \
      "6" "Upgrade eJabberd" \
      "7" "Upgrade DB" \
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
        echo 15 | dialog --title "Upgrade OSP" --gauge "Upgrade Nginx-OSP" 10 70 0
        upgrade_nginxcore
        echo 20 | dialog --title "Upgrade OSP" --gauge "Upgrading OSP-RTMP" 10 70 0
        upgrade_rtmp
        echo 30 | dialog --title "Upgrade OSP" --gauge "Upgrading ejabberd" 10 70 0
        upgrade_ejabberd
        echo 50 | dialog --title "Upgrade OSP" --gauge "Restarting ejabberd" 10 70 0
        sudo systemctl restart ejabberd >> $OSPLOG 2>&1
        echo 75 | dialog --title "Upgrade OSP" --gauge "Restarting Nginx Core" 10 70 0
        sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
        echo 85 | dialog --title "Upgrade OSP" --gauge "Restarting OSP Core" 10 70 0
        sudo systemctl restart osp.target >> $OSPLOG 2>&1
        echo 90 | dialog --title "Installing OSP" --gauge "Upgrading Celery" 10 70 0
        upgrade_celery
        upgrade_celery_beat
        echo 95 | dialog --title "Upgrade OSP" --gauge "Restarting OSP-RTMP" 10 70 0
        sudo systemctl restart osp-rtmp >> $OSPLOG 2>&1
        result=$(echo "OSP - Single Server Upgrade Completed!")
        display_result "Upgrade OSP"
        ;;
      2 )
        echo 10 | dialog --title "Upgrade OSP" --gauge "Upgrading OSP Core" 10 70 0
        upgrade_osp
        echo 15 | dialog --title "Upgrade OSP" --gauge "Upgrade Nginx-OSP" 10 70 0
        upgrade_nginxcore
        echo 75 | dialog --title "Upgrade OSP" --gauge "Restarting Nginx Core" 10 70 0
        sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
        echo 85 | dialog --title "Upgrade OSP" --gauge "Restarting OSP Core" 10 70 0
        sudo systemctl restart osp.target >> $OSPLOG 2>&1
        echo 90 | dialog --title "Installing OSP" --gauge "Upgrading Celery" 10 70 0
        upgrade_celery
        result=$(echo "OSP - Core Upgrade Completed!")
        display_result "Upgrade OSP"
        ;;
      3 )
        echo 15 | dialog --title "Upgrade OSP" --gauge "Upgrade Nginx-OSP" 10 70 0
        upgrade_nginxcore
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
        echo 15 | dialog --title "Upgrade OSP" --gauge "Upgrade Nginx-OSP" 10 70 0
        upgrade_nginxcore
        echo 50 | dialog --title "Upgrade OSP" --gauge "Upgrading Edge" 10 70 0
        upgrade_edge
        sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
        result=$(echo "OSP-Edge Upgrade Completed!")
        display_result "Upgrade OSP"
        ;;
      5 )
        echo 30 | dialog --title "Upgrade OSP" --gauge "Upgrading OSP-Proxy" 10 70 0
        upgrade_proxy
        echo 70 | dialog --title "Upgrade OSP" --gauge "Restarting OSP-Proxy" 10 70 0
        sudo systemctl restart osp-proxy >> $OSPLOG 2>&1
        result=$(echo "OSP-Proxy Upgrade Completed!")
        display_result "Upgrade OSP"
        ;;
      6 )
        echo 15 | dialog --title "Upgrade OSP" --gauge "Upgrade Nginx-OSP" 10 70 0
        upgrade_nginxcore
        echo 30 | dialog --title "Upgrade OSP" --gauge "Upgrading ejabberd" 10 70 0
        upgrade_ejabberd
        echo 50 | dialog --title "Upgrade OSP" --gauge "Restarting ejabberd" 10 70 0
        sudo systemctl restart ejabberd >> $OSPLOG 2>&1
        echo 75 | dialog --title "Upgrade OSP" --gauge "Restarting Nginx Core" 10 70 0
        sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
        result=$(echo "eJabberd Upgrade Completed! You will need to edit /opt/ejabberd/conf/auth_osp.py again")
        display_result "Upgrade OSP"
        ;;
      7)
        upgrade_db
        result=$(echo "Database Upgrade Complete")
        display_result "Upgrade OSP"
    esac
  done
}

##########################################################
# Start Main Script Execution
##########################################################
sudo mkdir -p /var/log/osp/ >> /dev/null
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
        echo "install: Installs/Reinstalls OSP Components - Options: osp, osp-core, nginx, rtmp, edge, proxy, ejabberd"
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
          proxy )
            install_nginx_core >> $OSPLOG 2>&1
            install_osp_proxy >> $OSPLOG 2>&1
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
            upgrade_nginxcore
            upgrade_rtmp
            upgrade_ejabberd
            sudo systemctl restart ejabberd >> $OSPLOG 2>&1
            sudo systemctl restart nginx-osp >> $OSPLOG 2>&1
            sudo systemctl restart osp.target >> $OSPLOG 2>&1
            upgrade_celery
            upgrade_celery_beat
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
