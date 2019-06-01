# Open Streaming Platform

[![N|Solid](https://i.imgur.com/iKfwtyS.jpg)](https://i.imgur.com/4RV5IXH.jpg)

**Open Streaming Platform (OSP) is an open-source, RTMP streamer software front-end for [Arut's NGINX RTMP Module](https://github.com/arut/nginx-rtmp-module).**

OSP was designed a self-hosted alternative to services like Twitch.tv, Ustream.tv, and Youtube Live.

**OSP is still considered Beta and is not complete**

## Features:
 - RTMP Streaming from an input source like Open Broadcast Software (OBS).
 - Multiple Channels per User, allowing a single user to broadcast multiple streams at the same time without needing muiltiple accounts.
 - Video Stream Recording and On-Demand Playback. [![N|Solid](https://i.imgur.com/4RV5IXH.jpg)](https://i.imgur.com/4RV5IXH.jpg)
 - Per Channel Real-Time Chat for Video Streams. [![N|Solid](https://i.imgur.com/c598KLa.jpg)](https://i.imgur.com/c598KLa.jpg)
 - Real-Time Chat Moderation by Channel Owners (Banning/Unbanning)
 - Admin Controlled Adaptive Streaming
 - Protected Streams to allow access only to the audience you want.
 - Live Channels - Keep chatting and hang out when a stream isn't on
 - Webhooks - Connect OSP to other services via fully customizable HTTP requests which will pass information
 - Embed your stream or video directly into another web page easily
 - Share channels or videos via Facebook or Twitter quickly

## Planned Features:
 - Subscribe to a Channel and Get Notified on When a New Stream Starts.

## Tech

Open Streaming Platform uses a number of open source projects to work properly:

* [Python 3]
* [Gunicorn] - Python WSGI HTTP Server, Acts as a Reverse Proxy for Flask
* [Flask] - Microframework for Python based on Werkzeug & Jinja 2
* [Flask SQL-Alchemy] - Provide the Database for OSP
* [Flask Security] - Handle User Accounts, Login, and Registration
* [Flask Uploads] - Manage User Uploads, such as Pictures
* [Flask-RestPlus] - Handling and Documentation of the OSP API
* [Bootstrap] - For Building responsive, mobile-first projects on the web 
* [Bootstrap-Toggle] - Used to Build Toggle Buttons with Bootstrap
* [NGINX] - Open-Source, high-performance HTTP server and reverse proxy
* [NGINX-RTMP-Module] - NGINX Module for RTMP/HLS/MPEG-DASH live streaming
* [Socket.io] - Real-Time Communications Engine Between Client and Server
* [Flask Socket.io] - Interface Socket.io with Flask
* [Video.js] - Handles the HTML5 Video Playback of HLS video streams and MP4 Files
* [Font Awesome] - Interface Icons and Such
* [[Animista](http://animista.net/)] - Awesome CSS Animation Generator

And OSP itself is open source with a [public repository](https://gitlab.com/Deamos/flask-nginx-rtmp-manager) on Gitlab.

## Git Branches

OSP's Git Branches are setup in the following configuration
* **master** - Current Release Branch
* **release/(Version)** - Previous Official Releases
* **development** - Current Nightly Branch for OSP vNext
* **feature/(Name)** - In-progress Feature Builds to be merged with the Development Branch   

## Installation

### Standard Install
OSP has only been tested on Ubuntu 18.04 and Recent Debian Builds. The installation script may not work properly on other OS's.

Clone the Gitlab Repo
```
git clone https://gitlab.com/Deamos/flask-nginx-rtmp-manager.git
```

Run the install script
```
cd flask-nginx-rtmp-manager/setup
sudo bash setup-osp.sh
```

The installation script will install the files in the following location:
* **Video Files, Video Stream Files, and User Uploaded Images**: /var/www
* **OSP Files**: /opt/osp

Rename the Configuration File
```
cd /opt/osp/conf
sudo mv config.py.dist config.py
```
Edit the Default Values in the Configuration File
```
vi config.py
```
Change the following values from their Default:
* dbLocation - By Default, OSP uses SQLite, but you can change this value to use MySQL if you would like.
* secretKey - Flask Secret Key, change this!
* passwordSalt - Flask Security uses this value for Salting User Passwords, change this!

Restart the OSP service
```
sudo systemctl restart osp
```
Open a Web Browser and configure OSP
```
http://[SERVER IP]/
```

### Docker Install

A Dockerfile has been provided for running OSP in a container.  However due to the way NginX, Gunicorn, Flask, and Docker work, for OSP to work properly, the Frontend must be exposed using Port 80 or 443 and the RTSP port from OBS or other streaming software must be exposed on Port 1935.

This accomplished easily by using a reverse proxy in Docker such as Traefik.  However, Port 1935 will not be proxied and must be mapped to the same port on the host.

**Recommended Volumes/Mount Points**
* /var/www - Storage of Images, Streams, and Stored Video Files
* /opt/osp/conf/config.py - DB configuration and Password Salt Settings
* /opt/osp/db/database.db - Initial SQLite DB File
* /usr/local/nginx/conf - Contains the NginX Configuration files which can be altered to suit your needs (HTTPS without something like Traefik)

### Manual Install

1: Clone the Repo
```
cd /opt
git clone https://gitlab.com/Deamos/flask-nginx-rtmp-manager.git /opt/osp
```
2: Install Python 3 if not installed
```
sudo apt-get install python3 python3-pip
```
3: Install NGINX and NGINX-RTMP Dependencies
```
sudo apt-get install build-essential libpcre3 libpcre3-dev libssl-dev
```
4: Install Python Dependencies
```
pip3 install -r /opt/osp/setup/requirements.txt
```
5: Install Gunicorn and the uWSGI plugins
```
apt-get install gunicorn3 uwsgi-plugin-python
```
6: Download and Build NGINX and NGINX-RTMP
```
cd /tmp
wget "http://nginx.org/download/nginx-1.13.10.tar.gz"
wget "https://github.com/arut/nginx-rtmp-module/archive/master.zip"
wget "http://www.zlib.net/zlib-1.2.11.tar.gz"
tar xvfz nginx-1.13.10.tar.gz
unzip master.zip
tar xvfz zlib-1.2.11.tar.gz
cd nginx-1.13.10
./configure --with-http_ssl_module --add-module=../nginx-rtmp-module-master --with-zlib=../zlib-1.2.11
make
make install
```
7: Copy the NGINX conf file to the configuration directory
```
cp /opt/osp/setup/nginx/nginx.conf /usr/local/nginx/conf/nginx.conf
```
8: Copy the Gunicorn and NGINX SystemD files
```
cp /opt/osp/setup/nginx/nginx.service /lib/systemd/system/nginx.service
cp /opt/osp/setup/gunicorn/osp.service /lib/systemd/system/osp.service
```
9: Reload SystemD
```
systemctl daemon-reload
systemctl enable nginx.service
systemctl enable osp.service
```
10: Make the Required OSP Directories and Set Ownership
```
mkdir /var/www
mkdir /var/www/live
mkdir /var/www/videos
mkdir /var/www/live-rec
mkdir /var/www/images
mkdir /var/www/live-adapt
mkdir /var/stream-thumb
mkdir /var/log/gunicorn
chown -R www-data:www-data /var/www
chown -R www-data:www-data /opt/osp
chown -R www-data:www-data /opt/osp/.git
chown -R www-data:www-data /var/log/gunicorn
```
11: Install FFMPEG3
```
add-apt-repository ppa:jonathonf/ffmpeg-3 -y
apt-get update
apt-get install ffmpeg -y
```
12: Start NGINX and OSP
```
systemctl start nginx.service
systemctl start osp.service
```
13: Open the site in a browser and run through the First Time Setup
```
http://<ip or host>/
```

### Usage

**A Channel and Stream key must be created prior to streaming.**

Set your OBS client to stream at:
```
rtsp://[serverip]/stream
```

**Important Note**: 
- By default, OSP uses HTTP instead of HTTPS.  It is recommend to get a TLS certificate and configure NGINX to use HTTPS prior to production use.
- NGINX Conf Files located at /usr/local/nginx/conf/
- If you plan on using Lets Encrypt, please use the Cert Only method for verification, as NGINX is configured from source and can cause problems with the Certbot automated process.

## API
OSP's API can be reached at the following Endpoint:
```
http://[serverIP/FQDN]/apiv1/
```
Usage of the API required a streamer create an API key.

The API is self-documenting using Swagger-UI.

To use an authenticated endpoint, ensure you are adding 'X-API-KEY':'\<Your API KEY>' to the request headers.

## Upgrading

### Standard Upgrade
* Backup your Database File:
```
cp /opt/osp/db/database.db /opt/osp/db/database.bak
```
* Perform a Git Pull
```
cd /opt/osp
sudo git pull
```
* Reset Ownership of OSP back to www-data
```
sudo chown -R www-data:www-data /opt/osp
```
* Run the DB Upgrade Script to Ensure the Database Schema is up-to-date
```
bash dbUpgrade.sh
```

### Upgrading from Alpha4 to Beta1
With the move to Beta1, to support channel protections it is recommended to replace your nginx.conf file with the new configuration to support this feature. To do so, run the beta1upgrade.sh script to ensure all settings and directories are created.
```
cd /opt/osp/setup/other
sudo bash alpha4tobeta1.sh
``` 
After completion, your original nginx.conf file will be renamed to nginx.conf.old and you make adjustments to the new file.

### Upgrading from Alpha3 to Alpha4
Due to the changes from Python 2 to Python 3, You need to run a script to remove Python 2.7 and its modules and replace them with Python 3
* Perform a Git Pull
* Run the Upgrade Script
```
cd /opt/osp/setup/other
sudo bash alpha3toalpha4.sh
```

### Upgrading from Pre-Alpha3
* If you are updating from pre-Alpha3 and use SQLite, save a backup copy of your database.db file and config.py files in a safe location outside of /opt/osp.
* Remove the /opt/osp directory and perform a fresh install then move your database.db file to /opt/osp/db and your config.py to /opt/osp/conf.
* Edit your config.py file and change the dbLocation variable to be the following:
```
dbLocation = 'sqlite:///db/database.db'
```
* Restart the OSP Service
```
sudo service osp restart
```

## Other Info
### Chat Comands
- /ban <username> - Bans a user from chatting in a chat room
- /unban <username> - Unbans a user who has been banned
- /mute - Places a Chat Channel on Mute
- /unmute - Removes a Mute Placed on a Chat Channel

### Webhooks
Webhooks allow you to send a notification out to other services using a GET/POST/PUT/DELETE request which can be defined on a per channel basis depending on various triggers.

OSP currently supports the following triggers:
- At the Start of a Live Stream
- At the End of a Live Stream
- On a New Viewer Joining a Live Stream
- On a Stream Upvote
- On a Stream Metadata Change (Name/Topic)
- On a Stream Chat Message
- On Posting of a New Video to a Channel
- On a New Video Comment
- On a Video Upvote
- On a Video Metadata Change (Name/Topic)

When defining your webhook payload, you can use variables which will be replaced with live data at the time the webhook is run.  Webhook variables are defined as the following:
- %channelname%
- %channelurl%
- %channeltopic%
- %channelimage%
- %streamer%
- %channeldescription%
- %streamname%
- %streamurl%
- %streamtopic%
- %streamimage%
- %user%
- %userpicture%
- %videoname%
- %videodate%
- %videodescription%
- %videotopic%
- %videourl%
- %videothumbnail%
- %comment%

Example Webhook for Discord:

- Type: **POST**
- Trigger Event: **Stream Start**

Header
```json
{
  "Content-Type": "application/json"
}
```

Payload
```json
{
  "content": "%channelname% went live on OSP Test",
  "username": "OSP Bot",
  "embeds": [
    {
      "title": "%streamurl%",
      "url": "https://%streamurl%",
      "color": 6570404,
      "image": {
        "url": "https://%channelimage%"
      },
      "author": {
        "name": "%streamer% is now streaming"
      },
      "fields": [
        {
          "name": "Channel",
          "value": "%channelname%",
          "inline": true
        },
        {
          "name": "Topic",
          "value": "%streamtopic%",
          "inline": true
        },
        {
          "name": "Stream Name",
          "value": "%streamname%",
          "inline": true
        },
        {
          "name": "Description",
          "value": "%channeldescription%",
          "inline": true
        }
      ]
    }
  ]
}
```

### Adaptive Streaming
While OSP now supports the ability to transcode to an adaptive stream for lower bandwidth users, this feature will use considerable CPU processing poweer and may slow down your OSP instance.  It is recommended only to use this feature when there is either few streams occurring or if your server has sufficient resources to handle the ability to transcode multiple streams.

By default, NGINX-RTMP has only been configured to transcode 1080p, 720p, 480p, & 360p. You can optimize how streams are transcoded by editing the /usr/local/nginx/conf/nginx.conf file and following the instructions at https://licson.net/post/setting-up-adaptive-streaming-with-nginx/

### Theming
OSP Supports Custom HTML and CSS theming via creation of another directory under the /opt/osp/templates/themes directory.

Custom CSS can be created under the /opt/osp/static/css directory under the name $ThemeName.css.

When theming, all html files must be used.  Use the Default Theme as a template to build your own theme.

Themes also must contain a theme.json file to work properly with OSP.

theme.json: 
```json
{
  "Name": "Example",
  "Maintainer": "Some User",
  "Version": "1.0",
  "Description": "Description of Theme"
}
```

Thanks
----
Special thanks to the folks of the [OSP Discord channel](https://discord.gg/Jp5rzbD) for their testing and suggestions!

License
----

MIT License