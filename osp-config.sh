#!/bin/bash
# OSP Control Script

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

#######################################################
# Script Functions
#######################################################

display_result() {
  dialog --title "$1" \
    --no-collapse \
    --msgbox "$result" 20 70
}

reset_nginx() {
   RESETLOG="/opt/osp/logs/reset.log"
   echo 25 | dialog --title "Reset Nginx-RTMP Configuration" --gauge "Backup Nginx-RTMP Configurations" 10 70 0
   cp /usr/local/nginx/conf/nginx.conf /usr/local/nginx/conf/nginx.conf.bak >> $RESETLOG 2>&1
   echo 50 | dialog --title "Reset Nginx-RTMP Configuration" --gauge "Copying Nginx-RTMP Configurations" 10 70 0
   cp /opt/osp/setup/nginx/nginx.conf /usr/local/nginx/conf >> $RESETLOG 2>&1
   cp /opt/osp/setup/nginx/osp-rtmp.conf /usr/local/nginx/conf >> $RESETLOG 2>&1
   cp /opt/osp/setup/nginx/osp-redirects.conf /usr/local/nginx/conf >> $RESETLOG 2>&1
   cp /opt/osp/setup/nginx/osp-socketio.conf /usr/local/nginx/conf >> $RESETLOG 2>&1
   echo 50 | dialog --title "Reset Nginx-RTMP Configuration" --gauge "Restarting Nginx" 10 70 0
   systemctl restart nginx-osp $RESETLOG 2>&1
}

upgrade_db() {
  UPGRADELOG="/opt/osp/logs/upgrade.log"
  echo 0 | dialog --title "Upgrading Database" --gauge "Stopping OSP" 10 70 0
  systemctl stop osp.target >> $UPGRADELOG 2>&1
  echo 15 | dialog --title "Upgrading Database" --gauge "Upgrading Database" 10 70 0
  python3 manage.py db init >> $UPGRADELOG 2>&1
  echo 25 | dialog --title "Upgrading Database" --gauge "Upgrading Database" 10 70 0
  python3 manage.py db migrate >> $UPGRADELOG 2>&1
  echo 50 | dialog --title "Upgrading Database" --gauge "Upgrading Database" 10 70 0
  python3 manage.py db upgrade >> $UPGRADELOG 2>&1
  echo 75 | dialog --title "Upgrading Database" --gauge "Starting OSP" 10 70 0
  systemctl start osp.target >> $UPGRADELOG 2>&1
  echo 100 | dialog --title "Upgrading Database" --gauge "Complete" 10 70 0
}

upgrade_osp() {
   UPGRADELOG="/opt/osp/logs/upgrade.log"
   echo 0 | dialog --title "Upgrading OSP" --gauge "Pulling Git Repo" 10 70 0
   git stash > $UPGRADELOG 2>&1
   git pull >> $UPGRADELOG 2>&1
   echo 15 | dialog --title "Upgrading OSP" --gauge "Setting /opt/osp Ownership" 10 70 0
   chown -R $http_user:$http_user /opt/osp >> $UPGRADELOG 2>&1
   echo 25 | dialog --title "Upgrading OSP" --gauge "Stopping OSP" 10 70 0
   systemctl stop osp.target >> $UPGRADELOG 2>&1
   echo 30 | dialog --title "Upgrading OSP" --gauge "Stopping Nginx" 10 70 0
   systemctl stop nginx-osp >> $UPGRADELOG 2>&1
   echo 35 | dialog --title "Upgrading OSP" --gauge "Installing Python Dependencies" 10 70 0
   pip3 install -r /opt/osp/setup/requirements.txt >> $UPGRADELOG 2>&1
   echo 45 | dialog --title "Upgrading OSP" --gauge "Upgrading Nginx-RTMP Configurations" 10 70 0
   cp /opt/osp/setup/nginx/osp-rtmp.conf /usr/local/nginx/conf $UPGRADELOG 2>&1
   cp /opt/osp/setup/nginx/osp-redirects.conf /usr/local/nginx/conf $UPGRADELOG 2>&1
   cp /opt/osp/setup/nginx/osp-socketio.conf /usr/local/nginx/conf $UPGRADELOG 2>&1
   echo 50 | dialog --title "Upgrading OSP" --gauge "Upgrading Database" 10 70 0
   python3 manage.py db init >> $UPGRADELOG 2>&1
   echo 55 | dialog --title "Upgrading OSP" --gauge "Upgrading Database" 10 70 0
   python3 manage.py db migrate >> $UPGRADELOG 2>&1
   echo 65 | dialog --title "Upgrading OSP" --gauge "Upgrading Database" 10 70 0
   python3 manage.py db upgrade >> $UPGRADELOG 2>&1
   echo 75 | dialog --title "Upgrading OSP" --gauge "Starting OSP" 10 70 0
   systemctl start osp.target >> $UPGRADELOG 2>&1
   echo 90 | dialog --title "Upgrading OSP" --gauge "Starting Nginx" 10 70 0
   systemctl start nginx-osp >> $UPGRADELOG 2>&1
   echo 100 | dialog --title "Upgrading OSP" --gauge "Complete" 10 70 0
}

install_osp() {
  cwd=$PWD
  installLog=$cwd/install.log

  echo "Starting OSP Install" > $installLog
  echo 0 | dialog --title "Installing OSP" --gauge "Installing Linux Dependencies" 10 70 0

  if  $arch
  then
          echo "Installing for Arch" >> $installLog
          sudo pacman -S python-pip base-devel unzip wget git redis gunicorn uwsgi-plugin-python libpq-dev libmysqlclient-dev ffmpeg --needed >> $installLog 2>&1
          echo 5 | dialog --title "Installing OSP" --gauge "Installing Linux Dependencies" 10 70 0
          sudo pip3 install -r $cwd/setup/requirements.txt
  else
          echo "Installing for Debian - based" >> $installLog 2>&1

          # Get Dependencies
          sudo apt-get install build-essential libpcre3 libpcre3-dev libssl-dev unzip libpq-dev git -y >> $installLog 2>&1
          echo 5 | dialog --title "Installing OSP" --gauge "Installing Linux Dependencies" 10 70 0
          # Setup Python
          sudo apt-get install python3 python3-pip uwsgi-plugin-python3 python3-dev python3-setuptools -y >> $installLog 2>&1
          echo 7 | dialog --title "Installing OSP" --gauge "Installing Linux Dependencies" 10 70 0
          sudo pip3 install wheel >> $installLog 2>&1
          sudo pip3 install -r $cwd/setup/requirements.txt >> $installLog 2>&1

          # Install Redis
          sudo apt-get install redis -y >> $installLog 2>&1
  fi
  echo 10 | dialog --title "Installing OSP" --gauge "Configuring Redis" 10 70 0
  sudo sed -i 's/appendfsync everysec/appendfsync no/' /etc/redis/redis.conf >> $installLog 2>&1
  sudo systemctl restart redis >> $installLog 2>&1


  # Setup OSP Directory
  echo 20 | dialog --title "Installing OSP" --gauge "Setting up OSP Directory" 10 70 0
  mkdir -p /opt/osp >> $installLog 2>&1
  sudo cp -rf -R $cwd/* /opt/osp >> $installLog 2>&1
  sudo cp -rf -R $cwd/.git /opt/osp >> $installLog 2>&1

  # Build Nginx with RTMP module
  echo 25 | dialog --title "Installing OSP" --gauge "Downloading Nginx Source" 10 70 0
  if cd /tmp
  then
          sudo wget -q "http://nginx.org/download/nginx-1.17.3.tar.gz"
          echo 26 | dialog --title "Installing OSP" --gauge "Downloading Required Modules" 10 70 0
          sudo wget -q "https://github.com/arut/nginx-rtmp-module/archive/v1.2.1.zip"
          echo 27 | dialog --title "Installing OSP" --gauge "Downloading Required Modules" 10 70 0
          sudo wget -q "http://www.zlib.net/zlib-1.2.11.tar.gz"
          echo 28 | dialog --title "Installing OSP" --gauge "Downloading Required Modules" 10 70 0
          sudo wget -q "https://bitbucket.org/nginx-goodies/nginx-sticky-module-ng/get/master.tar.gz"
          echo 29 | dialog --title "Installing OSP" --gauge "Decompressing Nginx Source and Modules" 10 70 0
          sudo tar xfz nginx-1.17.3.tar.gz
          sudo unzip -qq -o v1.2.1.zip >> $installLog 2>&1
          sudo tar xfz zlib-1.2.11.tar.gz
          sudo tar xfz master.tar.gz
          echo 30 | dialog --title "Installing OSP" --gauge "Building Nginx from Source" 10 70 0
          if cd nginx-1.17.3
          then
                  ./configure --with-http_ssl_module --with-http_v2_module --with-http_auth_request_module --add-module=../nginx-rtmp-module-1.2.1 --add-module=../nginx-goodies-nginx-sticky-module-ng-08a395c66e42 --with-zlib=../zlib-1.2.11 --with-cc-opt="-Wimplicit-fallthrough=0" >> $installLog 2>&1
                  echo 35 | dialog --title "Installing OSP" --gauge "Installing Nginx" 10 70 0
                  sudo make install >> $installLog 2>&1
          else
                  echo "Unable to Build Nginx! Aborting." >> $installLog 2>&1
                  exit 1
          fi
  else
          echo "Unable to Download Nginx due to missing /tmp! Aborting." >> $installLog 2>&1
          exit 1
  fi

  # Grab Configuration
  echo 37 | dialog --title "Installing OSP" --gauge "Copying Nginx Config Files" 10 70 0
  if cd $cwd/setup/nginx
  then
          sudo cp *.conf /usr/local/nginx/conf/ >> $installLog 2>&1
  else
          echo "Unable to find downloaded Nginx config directory.  Aborting." >> $installLog 2>&1
          exit 1
  fi
  # Enable SystemD
  echo 38 | dialog --title "Installing OSP" --gauge "Setting up Nginx SystemD" 10 70 0
  if cd $cwd/setup/nginx
  then
          sudo cp nginx-osp.service /etc/systemd/system/nginx-osp.service >> $installLog 2>&1
          sudo systemctl daemon-reload >> $installLog 2>&1
          sudo systemctl enable nginx-osp.service >> $installLog 2>&1
  else
          echo "Unable to find downloaded Nginx config directory. Aborting." >> $installLog 2>&1
          exit 1
  fi

  # Install ejabberd
  echo 40 | dialog --title "Installing OSP" --gauge "Installing ejabberd" 10 70 0
  wget -O "/tmp/ejabberd-20.04-linux-x64.run" "https://www.process-one.net/downloads/downloads-action.php?file=/20.04/ejabberd-20.04-linux-x64.run" >> $installLog 2>&1
  sudo chmod +x /tmp/ejabberd-20.04-linux-x64.run $installLog 2>&1
  /tmp/ejabberd-20.04-linux-x64.run ----unattendedmodeui none --mode unattended --prefix /usr/local/ejabberd --cluster 0 >> $installLog 2>&1
  echo 42 | dialog --title "Installing OSP" --gauge "Installing ejabberd" 10 70 0
  ADMINPASS=$( cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1 )
  sed -i "s/CHANGE_EJABBERD_PASS/$ADMINPASS/" /opt/osp/conf/config.py.dist >> $installLog 2>&1
  mkdir /usr/local/ejabberd/conf >> $installLog 2>&1
  cp /opt/osp/setup/ejabberd/ejabberd.yml /usr/local/ejabberd/conf/ejabberd.yml >> $installLog 2>&1
  cp /usr/local/ejabberd/bin/ejabberd.service /etc/systemd/system/ejabberd.service >> $installLog 2>&1
  user_input=$(\
  dialog --nocancel --title "Setting up Ejabberd" \
         --inputbox "Enter your Site Address (Must match FQDN):" 8 80 \
  3>&1 1>&2 2>&3 3>&-)
  sudo sed -i "s/CHANGEME/$user_input/g" /usr/local/ejabberd/conf/ejabberd.yml>> $installLog 2>&1
  echo 45 | dialog --title "Installing OSP" --gauge "Installing ejabberd" 10 70 0
  sudo systemctl daemon-reload >> $installLog 2>&1
  sudo systemctl enable ejabberd >> $installLog 2>&1
  sudo systemctl start ejabberd >> $installLog 2>&1
  /usr/local/ejabberd/bin/ejabberdctl register admin localhost $ADMINPASS >> $installLog 2>&1

  echo 50 | dialog --title "Installing OSP" --gauge "Setting up Gunicorn SystemD" 10 70 0
  if cd $cwd/setup/gunicorn
  then
          sudo cp osp.target /etc/systemd/system/ >> $installLog 2>&1
          sudo cp osp-worker@.service /etc/systemd/system/ >> $installLog 2>&1
          sudo systemctl daemon-reload >> $installLog 2>&1
          sudo systemctl enable osp.target >> $installLog 2>&1
  else
          echo "Unable to find downloaded Gunicorn config directory. Aborting." >> $installLog 2>&1
          exit 1
  fi

  # Create HLS directory
  echo 60 | dialog --title "Installing OSP" --gauge "Creating OSP Video Directories" 10 70 0
  sudo mkdir -p "$web_root" >> $installLog 2>&1
  sudo mkdir -p "$web_root/live" >> $installLog 2>&1
  sudo mkdir -p "$web_root/videos" >> $installLog 2>&1
  sudo mkdir -p "$web_root/images" >> $installLog 2>&1
  sudo mkdir -p "$web_root/live-adapt" >> $installLog 2>&1
  sudo mkdir -p "$web_root/stream-thumb" >> $installLog 2>&1

  echo 70 | dialog --title "Installing OSP" --gauge "Setting Ownership of OSP Video Directories" 10 70 0
  sudo chown -R "$http_user:$http_user" "$web_root" >> $installLog 2>&1

  sudo chown -R "$http_user:$http_user" /opt/osp >> $installLog 2>&1
  sudo chown -R "$http_user:$http_user" /opt/osp/.git >> $installLog 2>&1

  #Setup FFMPEG for recordings and Thumbnails
  echo 80 | dialog --title "Installing OSP" --gauge "Installing FFMPEG" 10 70 0
  if [ "$arch" = "false" ]
  then
          sudo add-apt-repository ppa:jonathonf/ffmpeg-4 -y >> $installLog 2>&1
          sudo apt-get update >> $installLog 2>&1
          sudo apt-get install ffmpeg -y >> $installLog 2>&1
  fi

  # Setup Logrotate
  echo 90 | dialog --title "Installing OSP" --gauge "Setting Up Log Rotation" 10 70 0
  if cd /etc/logrotate.d
  then
      sudo cp /opt/osp/setup/logrotate/* /etc/logrotate.d/ >> $installLog 2>&1
  else
      sudo apt-get install logrorate >> $installLog 2>&1
      if cd /etc/logrotate.d
      then
          sudo cp /opt/osp/setup/logrotate/* /etc/logrotate.d/ >> $installLog 2>&1
      else
          echo "Unable to setup logrotate" >> $installLog 2>&1
      fi
  fi
  # Start Nginx
  echo 100 | dialog --title "Installing OSP" --gauge "Starting Nginx" 10 70 0
  sudo systemctl start nginx-osp.service >> $installLog 2>&1
  sudo mv $installLog /opt/osp/logs >> /dev/null 2>&1
}

##########################################################
# Start Main Script Execution
##########################################################

if [ $# -eq 0 ]
  then
    while true; do
      exec 3>&1
      selection=$(dialog \
        --backtitle "Open Streaming Platform - $VERSION" \
        --title "Menu" \
        --clear \
        --cancel-label "Exit" \
        --menu "Please select:" $HEIGHT $WIDTH 6 \
        "1" "Install/Reinstall OSP" \
        "2" "Restart Nginx" \
        "3" "Restart OSP" \
        "4" "Upgrade to Latest Build" \
        "5" "Upgrade DB Only" \
        "6" "Reset Nginx Configuration" \
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
          install_osp
          result=$(echo "OSP Install Completed! \n\nPlease copy /opt/osp/conf/config.py.dist to /opt/osp/conf/config.py, review the settings, and start the osp service by running typing sudo systemctl start osp.target\n\nAlso, Edit the /usr/local/ejabberd/conf/ejabberd.yml file per Install Instructions\n\nInstall Log can be found at /opt/osp/logs/install.log")
          display_result "Install OSP"
          ;;
        2 )
          systemctl restart nginx-osp > /dev/null 2>&1
          restartStatus=$(systemctl is-active nginx-osp) > /dev/null 2>&1
          if [[ $restartStatus -eq Active ]]; then
            result=$(echo Nginx Restarted Successfully!)
          else
            result=$(echo Nginx Failed to Restart!)
          fi
          display_result "Restart Nginx"
          ;;
        3 )
          systemctl restart osp.target > /dev/null 2>&1
          worker5000=$(systemctl is-active osp-worker@5000) > /dev/null 2>&1
          worker5001=$(systemctl is-active osp-worker@5001) > /dev/null 2>&1
          worker5002=$(systemctl is-active osp-worker@5002) > /dev/null 2>&1
          worker5003=$(systemctl is-active osp-worker@5003) > /dev/null 2>&1
          worker5004=$(systemctl is-active osp-worker@5004) > /dev/null 2>&1
          worker5005=$(systemctl is-active osp-worker@5005) > /dev/null 2>&1
          worker5006=$(systemctl is-active osp-worker@5006) > /dev/null 2>&1
          worker5007=$(systemctl is-active osp-worker@5007) > /dev/null 2>&1
          worker5008=$(systemctl is-active osp-worker@5008) > /dev/null 2>&1
          worker5009=$(systemctl is-active osp-worker@5009) > /dev/null 2>&1
          worker5010=$(systemctl is-active osp-worker@5010) > /dev/null 2>&1
          result=$(echo "Worker 5000: $worker5000\nWorker 5001: $worker5001\nWorker 5002: $worker5002\nWorker 5003: $worker5003\nWorker 5004: $worker5004\nWorker 5005: $worker5005\nWorker 5006: $worker5006 \nWorker 5007: $worker5007 \nWorker 5008: $worker5008 \nWorker 5009: $worker5009\nWorker 5010: $worker5010")
          display_result "OSP Worker Status after Restart"
          ;;
        4 )
          cd /opt/osp > /dev/null 2>&1
          gitStatus=$(git branch)
          if [[ ! -d .git ]]; then
            result=$(echo "OSP not setup with Git.\n\n Please clone OSP Repo and try again")
          else
            git fetch > /dev/null 2>&1
            BRANCH=$(git rev-parse --abbrev-ref HEAD) > /dev/null 2>&1
            CURRENTCOMMIT=$(git rev-parse HEAD) > /dev/null 2>&1
            REMOTECOMMIT=$(git rev-parse origin/$BRANCH) > /dev/null 2>&1
            NEWVERSION=$(curl -s https://gitlab.com/Deamos/flask-nginx-rtmp-manager/-/raw/$BRANCH/version) > /dev/null 2>&1
            if [[ $CURRENTCOMMIT == $REMOTECOMMIT ]]; then
              result=$(echo "OSP is up-to-date on Branch $BRANCH")
            else
              dialog --title "Upgrade to Latest Build" \
                     --yesno "Would you like to update your current install to the new commit?\n\nCurrent:$BRANCH/$VERSION$CURRENTCOMMIT\nRepository:$BRANCH/$NEWVERSION$REMOTECOMMIT" 20 80
              response=$?
              case $response in
                 0 )
                   upgrade_osp
                   UPGRADECHECKVERSION="/opt/osp/setup/upgrade/${NEWVERSION::-1}.sh"
                   if [[ -f $UPGRADECHECKVERSION ]]; then
                      bash $UPGRADECHECKVERSION >> /opt/osp/logs/${NEWVERSION::-1}.log 2>&1
                   fi
                   version=$NEWVERSION
                   result=$(echo "OSP $BRANCH/$VERSION$CURRENTCOMMIT has been updated to $BRANCH/$NEWVERSION$REMOTECOMMIT\n\nUpgrade logs can be found at /opt/osp/logs/upgrade.log")
                   ;;
                 1 )
                   result=$(echo "Canceled Update to $BRANCH/$NEWVERSION$REMOTECOMMIT")
                   ;;
              esac
            fi
          fi
          display_result "Upgrade Results"
          ;;
        5 )
          upgrade_db
          result=$(echo "Database Upgrade Complete!")
          display_result "Upgrade Results"
          ;;
        6 ) reset_nginx
          result=$(echo "Nginx Configuration has been reset.\n\nBackup of nginx.conf was stored at /usr/local/nginx/conf/nginx.conf.bak")
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
        echo "install: Installs/Reinstalls OSP"
        echo "restartnginx: Restarts Nginx"
        echo "restartosp: Restarts OSP"
        echo "upgrade: Upgrades OSP"
        echo "dbupgrade: Upgrades the Database Only"
        echo "resetnginx: Resets the Nginx Configuration and Restarts"
        ;;
      install )
        install_osp
        ;;
      restartnginx )
        systemctl restart nginx-osp
        ;;
      restartosp )
        systemctl restart osp.target
        ;;
      upgrade )
        upgrade_osp
        ;;
      dbupgrade )
        upgrade_db
        ;;
      resetnginx )
        reset_nginx
        ;;
    esac
    fi

#######################################################
# End
#######################################################