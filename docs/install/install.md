# Installation
## Requirements
OSP has been verified to work with the following requirements

- Ubuntu 20.04 or later, Debian 10 or later
- Python 3.8 or later
- MySQL 5.7.7 or later, or MariaDB > 10.1, if not using SQLite
- SMTP Mail Server for Email Address Validation and Subscriptions
- FFMPEG 4 or greater
- Dual Core Processor at 2.4 Ghz
- 4 GB RAM
- 120 GB HDD Storage
- Upstream Bandwidth > 35Mbps for 720p/30fps  Streams to 10 people @  3500kbps bit rate

## Install Open Streaming Platform
### Script Install - Single Server (OSP-Core, OSP-RTMP, Ejabberd, Redis, MySQL)
1) Clone the git repository
```bash
git clone https://gitlab.com/Deamos/flask-nginx-rtmp-manager.git
```
2) Install the Config Tool Prerequisites (if not already installed)
```bash
sudo apt-get install dialog
```
3) Run the OSP Configuration Tool
```bash
cd flask-nginx-rtmp-manager
sudo bash osp-config.sh
```
4) Select Option 1 - "Install..."
5) Select Option 1 - "Install OSP - Single Server"
6) During the install process, the Config Tool will ask for an Ejabberd Full Qualified Domain Name (FQDN). This should be the same as the public domain name which will be used to access OSP. This should be a valid DNS entry as it is used to configure Ejabberd's Chat Domain and by default is used by the chat client to connect users to the XMPP chat system. IP addresses may not function properly.
7) On completion, exit the OSP Config Tool.
8) Review the values in the OSP /opt/osp/conf/config.py.
> **_NOTE:_** secretKey and passwordSalt should be changed from their default values.
```bash
sudo nano /opt/osp/conf/config.py
```
9) Restart the OSP Core Workers
```bash
sudo systemctl restart osp.target
```
To test streaming on the server, see the "Testing OSP server" section of the [Streaming](/Usage/Streaming) page.
### Script Install - Split Server Install - OSP Components on Different Servers
Starting with OSP version 0.8.0, OSP components can be split over multiple servers. This helps with spreading the load required for a busy OSP install with many viewers. In addition, splitting the components can be useful to set up load balancing by having multiple copies of the component and using a load balancer, such as HAproxy.
To perform a Split Server Setup, please review the following requirements:
* **Componentaization** - Multiple components can be installed on a single server to reduce cost. Doing so can also prevent needing some of the considerations in this list. For Example, if you consolidate OSP-Core and OSP-RTMP and do not require OSP-Edge Servers, you will not need Centralized storage as they
* **Centralized Storage** - OSP requires some form of mounted centralized storage for Videos, Clips, & Stream/Video Thumbnails. This can be accomplished easily by using an S3-based storage bucket and using s3fs to mount the bucket to the servers file systems. Another method would be a NFS mount in the require location. Below is the required drive mounts and locations
* **Mounts**
* /var/www/videos - OSP-Core, OSP-RTMP
* /var/www/stream-thumb - OSP-Core, OSP-RTMP
* /var/www/images - OSP-Core
* **SSL/TLS** - If OSP Core systems use HTTPS with SSL/TLS certificates, certificates will also be needed for the Ejabberd, Edge, Proxy, or OSP-RTMP (Only if using Proxy) Servers to prevent issues with HTTP(s) mixed content.
* **MySQL & Redis** - the OSP Config Tool does not have an option for MySQL and Redis installs. It is recommended to be familar with their install and configuration prior to a Split Server Install
In some instances, some services can be co-located on the same server. See rules below:
* OSP-Core, OSP-RTMP, Redis, ejabberd, and Database can exist on the same server
* OSP-Edge can not exist on the same server as OSP-RTMP
* OSP-Proxy can not exist on the same server as OSP-Edge, OSP-Core, OSP-RTMP, or ejabberd
#### Recommended Install Order
Below is the recommended order of setting up split servers. This is due to some of the dependancies requires for some servers to function properly.
1) Centralized Storage - Have a server ready to connect to
2) Ejabberd
3) Redis
4) Database
5) OSP-Core
6) OSP-RTMP
7) OSP-Edge
8) OSP-Proxy
#### **Centralized Storage Mounting (Use with OSP-Core and OSP-RTMP)**
These instructions are intended to be used **after the OSP-Core and OSP-RTMP install processes**. After installing the OSP components, it is recommended to determine and establish a central storage server setup on completion of component deployment.
Due to the many possible configurations of using central, shared storage, it is impossible to cover a "best" method for doing so. For the purposes of this documentation, it is assumed that an S3-compatable bucket will be used and mounting is covered below using s3fs.
**DO NOT USE s3fs 1.86-1.**
**A critical bug in caching can lead to mount failure of the s3 bucket, leading to loss of recordings. Currently the latest Ubuntu LTS (20.04) only has this version of s3fs available.**
1) Install s3fs
```bash
sudo apt-get update && sudo apt-get install s3fs
```
2) Create a password file. This will contain the S3 key and secret token:
```bash
echo S3KEY:S3TOKEN > ~/.passwd-s3fs
```
3) Set the permissions to secure the file
```bash
chmod 600 ~/.passwd-s3fs
```
4) Edit the Fuse Configurations to allow access by non-root users to files
```bash
sudo nano /etc/fuse.conf
```
5) Comment out the following line ```user_allow_other```
6) Identify and write down the uid and gid of the www-data user. Example: ```uid=33(www-data) gid=33(www-data) groups=33(www-data)```
```bash
sudo -u www-data id
```
7) Create the required stub locations:
```bash
sudo mkdir -p /var/www/videos
sudo mkdir -p /var/www/images
sudo mkdir -p /var/www/stream-thumb
```
8) Mount the directories to the S3-compatible bucket using your S3 Credentials and the identified UID & GID frm Step 6
```bash
s3fs <space_name> /var/www/videos -o url=<s3 endpoint> -o use_cache=/tmp -o allow_other -o use_path_request_style -o uid=<UID> -o gid=<GID>
s3fs <space_name> /var/www/images -o url=<s3 endpoint> -o use_cache=/tmp -o allow_other -o use_path_request_style -o uid=<UID> -o gid=<GID>
s3fs <space_name> /var/www/stream-thumb -o url=<s3 endpoint> -o use_cache=/tmp -o allow_other -o use_path_request_style -o uid=<UID> -o gid=<GID>
```
9) Verify the Mount was successful. The buckets should show as a s3fs mount at the bottom of the output
```bash
mount
```
> Note: To mount persistently, you can add the following to your fstab file
```
s3fs#<bucket_name> /var/www/images fuse url=<endpoint_url>,use_cache=/tmp,allow_other,use_path_request_style,_netdev,uid=33,gid=33 0 0
```
#### Ejabberd
1) Clone the git repository
```bash
git clone https://gitlab.com/Deamos/flask-nginx-rtmp-manager.git
```
2) Install the Config Tool Prerequisites (if not already installed)
```bash
sudo apt-get install dialog
```
3) Run the OSP Configuration Tool
```bash
cd flask-nginx-rtmp-manager
sudo bash osp-config.sh
```
4) Select Option 1 - "Install..."
5) Select Option 6 - "Install Ejabberd"
6) During the install process, the Config Tool will ask for an Ejabberd Full Qualified Domain Name (FQDN). This should be the same as the public domain name which will be used to access OSP. This should be a valid DNS entry. Use of an IP address may not function properly.
7) On completion, exit the OSP Config Tool.
8) Setup a new Ejabberd admin account.
```bash
sudo /usr/local/ejabberd/bin/ejabberdctl register admin localhost <password>
```
9) Edit the ejabberd.yml
```bash
sudo nano /usr/local/ejabberd/conf/ejabberd.yml
```
10) Change the following lines to match your expected configuration:
* Line 43-44
```yaml
port: 5443
ip: "::"
```
* Line 55-56
```yaml
port: 5280
ip: "::"
```
* Line 77-78
```yaml
port: 4560
ip: "::"
```
* Line 91-93 (Add one line per OSP core or use CIDR Notation to allow a block of IPs)
```yaml
ip:
- 127.0.0.0/8
- ::1/128
- <ip address of OSP Core>
```
11) Save the ejabberd.yml file
12) Edit the auth_osp.py Authentication Handler
```
sudo nano /usr/local/ejabberd/conf/auth_osp.py
```
13) Edit the protocol and ospAPIServer variables to match your OSP Core Instance.
```python
protocol = "https"
ospAPIServer = "osp.example.com"
```
14) Save the auth_osp.py file
15) Restart Ejabberd
```bash
sudo systemctl restart ejabberd
```
#### Redis
1) Install Redis
```bash
sudo apt update
sudo apt install redis-server
```
2) Edit the redis.conf file
```bash
sudo nano /etc/redis/redis.conf
```
3) Find & Edit the bind location to listen on all interfaces
```conf
bind 0.0.0.0
```
4) Find and Set a Redis Password
```conf
requirepass <Password>
```
5) Save the redis.conf file
6) Restart Redis
```bash
sudo systemctl restart redis.service
```
#### Database
1) Install MariaDB
```bash
sudo apt-get update && sudo apt-get install mariadb-server
```
2) Download the OSP Modifications for MariaDB
```bash
sudo wget "https://gitlab.com/Deamos/flask-nginx-rtmp-manager/-/raw/master/setup/mysql/mysqld.cnf" -O /etc/mysql/my.cnf
```
3) Edit the my.cnf file
```bash
sudo nano /etc/mysql/my.cnf
```
4) Edit the bind-bind address to listen on all interfaces
```cnf
bind-address = 0.0.0.0
```
5) Restart MariaDB
```bash
sudo systemctl restart mysql
```
6) Log into MariaDB
```bash
sudo mysql
```
7) Create the Database & User. Be aware the remote server ips should be the IP address(es) of the OSP-Core Systems (See https://mariadb.com/kb/en/configuring-mariadb-for-remote-client-access/#granting-user-connections-from-remote-hosts)
```sql
CREATE DATABASE osp;
CREATE USER '<username>'@'<remote_server_ip>' IDENTIFIED BY '<password>';
GRANT ALL PRIVILEGES ON osp.* TO '<username>'@'<remote_server_ip>';
```
8) Quit the MariaDB Console
```sql
quit;
```
9) The Database will be initialized on the successful run of an OSP-Core Instance
#### OSP-Core
1) Clone the git repository
```bash
git clone https://gitlab.com/Deamos/flask-nginx-rtmp-manager.git
```
2) Install the Config Tool Prerequisites (if not already installed)
```bash
sudo apt-get install dialog
```
3) Run the OSP Configuration Tool
```bash
cd flask-nginx-rtmp-manager
sudo bash osp-config.sh
```
4) Select Option 1 - "Install..."
5) Select Option 2 - "Install OSP-Core"
6) On completion, exit the OSP Config Tool.
7) Copy the OSP config.py.dist file to config.py
```bash
sudo cp /opt/osp/conf/config.py.dist /opt/osp/conf/config.py
```
8) Edit the config.py file
```bash
sudo nano /opt/osp/conf/config.py
```
9) Change the dbLocation variable to match your database credentials and IP/DNS
```python
dbLocation = 'mysql+pymysql://<user>:<password>@<db_host>/<db_name>?charset=utf8mb4'
```
10) Change the Redis variables to match the IP/DNS and password set for it
```python
redisHost="redis.example.com"
redisPort=6379
redisPassword="redis_password"
```
11) Change the Ejabberd variables to match your configuration
```python
ejabberdAdmin = "admin" <--Leave this as admin
ejabberdPass = "ejabberd_admin_password"
ejabberdHost = "localhost" <--Leave this as localhost
ejabberdServer ="ejabberd.example.com"
```
12) Review the values in the OSP /opt/osp/conf/config.py.
> **_NOTE:_** secretKey and passwordSalt should be changed from their default values.
```bash
sudo nano /opt/osp/conf/config.py
```
13) Restart the OSP Core Workers
```bash
sudo systemctl restart osp.target
```
14) Save the config.py file
15) Initialize the Database by running the command line upgrader
```bash
sudo bash osp-config.sh upgrade db
```
16) Open a web browser and browse to:
```http://<OSPCore IP Address or DNS>```
17) Setup OSP using the Initial Configuration Wizard
#### OSP-RTMP
1) Clone the git repository
```bash
git clone https://gitlab.com/Deamos/flask-nginx-rtmp-manager.git
```
2) Install the Config Tool Prerequisites (if not already installed)
```bash
sudo apt-get install dialog
```
3) Run the OSP Configuration Tool
```bash
cd flask-nginx-rtmp-manager
sudo bash osp-config.sh
```
4) Select Option 1 - "Install..."
5) Select Option 3 - "Install OSP-RTMP"
6) On completion, exit the OSP Config Tool.
7) Copy and Edit the OSP-RTMP config.py file
```bash
sudo cp /opt/osp-rtmp/conf/config.py.dist /opt/osp-rtmp/conf/config.py
sudo nano /opt/osp-rtmp/conf/config.py
```
8) Change the ospCoreAPI Variable to point at your OSP-Core instance
```python
ospCoreAPI = "http://ospcore.example.com"
```
9) Start the OSP-RTMP Instance
```bash
sudo systemctl start osp-rtmp
```
10) Open a web browser and go to your OSP-Core Instance
```
http://ospcore.example.com
```
11) Log on as an Admin and Open the Admin Settings
12) Select RTMP Servers
13) Click the Plus Sign Button
14) Type in the IP or Fully Qualified Domain Name for your OSP-RTMP Server and click Add
#### OSP-Edge
1) Clone the git repository
```bash
git clone https://gitlab.com/Deamos/flask-nginx-rtmp-manager.git
```
2) Install the Config Tool Prerequisites (if not already installed)
```bash
sudo apt-get install dialog
```
3) Run the OSP Configuration Tool
```bash
cd flask-nginx-rtmp-manager
sudo bash osp-config.sh
```
4) Select Option 1 - "Install..."
5) Select Option 4 - "Install OSP-Edge"
6) When prompted, input the IP address of your OSP-RTMP Instance
7) On completion, exit the OSP Config Tool.
8) If you need to add additional authorized OSP-RTMP Instances, edit the osp-edge-rtmp.conf file for Nginx
```bash
sudo nano /usr/local/nginx/conf/services/osp-edge-rtmp.conf
```
9) Add any additional authorize publishing IPs to stream-data and stream-data-adapt:
```conf
allow publish <IP Address>;
```
10) Restart Nginx
```bash
sudo systemctl restart nginx-osp
```
12) Open a web browser and go to your OSP-Core Instance
```
http://ospcore.example.com
```
13) Log on as an Admin and Open the Admin Settings
14) Select Edge Streamers
15) Add the Fully Qualified Domain Name or IP Address of the Edge Server
16) Add the Load Percentage that the Edge Server will use.
> **_NOTE:_** The sum of all Edge Servers must equal 100%.
17) Restart Nginx on all OSP-Core Servers
```bash
sudo systemctl restart nginx-osp
```
#### OSP-Proxy
1) Clone the git repository
```bash
git clone https://gitlab.com/Deamos/flask-nginx-rtmp-manager.git
```
2) Install the Config Tool Prerequisites (if not already installed)
```bash
sudo apt-get install dialog
```
3) Run the OSP Configuration Tool
```bash
cd flask-nginx-rtmp-manager
sudo bash osp-config.sh
```
4) Select Option 1 - "Install..."
5) Select Option 5 - "Install OSP-Proxy"
6) When prompted, input the Protocol and Fully Qualified Domain Name of your OSP-Core Instance (ex: https://osp.example.com)
7) On completion, exit the OSP Config Tool.
8) If you are using TLS/SSL on your Core Site, Acquire a TLS Certificate
9) Edit /usr/local/nginx/conf/custom/osp-proxy-custom-servers.conf
```bash
sudo nano /usr/local/nginx/conf/custom/osp-proxy-custom-servers.conf
```
10) Change Line 8 to match your OSP Core FQDN
```
valid_referers server_names osp.example.com ~.;
```
11) If you are using TLS, Comment the following Line:
```listen 80 default_server;```
12) Uncomment the following lines and add the TLS configuration:
```
# listen 443 ssl http2 default_server;
# ssl_certificate /etc/letsencrypt/live/osp.example.com/fullchain.pem;
# ssl_certificate_key /etc/letsencrypt/live/osp.example.com/privkey.pem;
# ssl_protocols TLSv1.2 TLSv1.3;
```
13) Edit the OSP-Proxy Configuration File
```bash
sudo nano /opt/osp-proxy/conf/config.py
```
14) Change the Flask Secret Key to a Random Value
```
# Flask Secret Key
secretKey="CHANGEME"
```
15) If you are dedicating the proxy to a specific source (An Edge or Another Proxy), uncomment the ForceDestination Lines and set to match your source
```
# Force Destination - Use to point to Specified Edge Server or Tiered Proxy. Uncomment to override API's RTMP List and use the destination you list
forceDestination = "edge.example.com"
forceDestinationType = "edge" # Choices are "edge", "proxy"
```
15) Restart Nginx-OSP and OSP-Proxy
```bash
sudo systemctl restart nginx-osp
sudo systemctl restart osp-proxy
```
16) Ensure all Edge or RTMP Servers are listed in the OSP-Core Admin Panel. OSP-Proxy will query the OSP API and generate configurations to handle the proxy connection to retrieve the HLS fragments.
17) Perform a first run of the Configuration File Generator
```bash
cd /opt/osp
sudo bash updateUpstream.sh
```
18) Connect to each OSP-RTMP/Single Server and perform the following on each:
- If using TLS on the Core, Generate a TLS certificate
- Edit the /usr/local/nginx/conf/custom/osp-rtmp-custom-authorizeproxy.conf
```bash
sudo nano /usr/local/nginx/conf/custom/osp-rtmp-custom-authorizeproxy.conf
```
- Add the IP Address of each OSP-Proxy that will be accessing the source for /stream-thumb, /live-adapt, and /live:
```
# allow <ip of proxy>;
allow 201.13.12.50;
allow 193.10.3.9;
```
- If using TLS, Edit the /usr/local/nginx/conf/custom/osp-rtmp-custom-server
```
sudo nano /usr/local/nginx/conf/custom/osp-rtmp-custom-server
```
- Comment out the first line, uncomment the TLS information and add your certificate info (Note: Port 5999 will stay the same):
```
#listen 5999 default_server;
### Comment Above and Uncomment/Edit Below for OSP-Proxy TLS ###
listen 5999 ssl http2 default_server;
ssl_certificate /etc/letsencrypt/live/osp.example.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/osp.example.com/privkey.pem;
ssl_protocols TLSv1.2 TLSv1.3;
```
- Restart the Nginx-OSP instance
```bash
sudo systemctl restart nginx-osp
```
18) If you forced an Edge Server on Step 14, Connect to the Edge Server and edit /usr/local/nginx/conf/locations/osp-edge-redirects.conf
```bash
sudo nano /usr/local/nginx/conf/custom/osp-edge-redirects.conf
```
- Comment the add_headers line for /edge and /edge-adapt
```
#add_header 'Access-Control-Allow-Origin' "*" always;
```
- Edit the custom referes file at /usr/local/nginx/conf/custom/osp-edge-custom-refer.conf
```
sudo nano /usr/local/nginx/conf/custom/osp-edge-custom-refer.conf
```
- Add the OSP Core Server to the Valid Referers list for /edge and /edge-adapt
```
valid_referers server_names osp.example.com ~.;
```
- Restart Nginx-OSP
```
sudo systemctl restart nginx-osp
```
19) Add the OSP-Proxy Domain to the OSP-Core's Admin Panel under Settings
20) Test a Stream and verify that the video is displaying

### Manual Install
Coming Soon

### Docker Install

A Dockerfile has been provided for running OSP in a container. However due to the way NginX, Gunicorn, Flask, and Docker work, for OSP to work properly, the Frontend must be exposed using Port 80 or 443 and the RTSP port from OBS or other streaming software must be exposed on Port 1935.
This accomplished easily by using a reverse proxy in Docker such as Traefik. However, Port 1935 will not be proxied and must be mapped to the same port on the host.
An external Redis server/container is required to handling asynchronous communications between the internal Gunicorn worker instances.
Dockerhub URL: https://hub.docker.com/r/deamos/openstreamingplatform
```
docker pull deamos/openstreamingplatform
```
#### Environment Variables
DB_URL: Sets the SQLAlchemy URL String for the used DB.
Default: "sqlite:///db/database.db"
See https://docs.sqlalchemy.org/en/13/core/engines.html
FLASK_SECRET: Flask Secret Key
Format: "CHANGEME"
FLASK_SALT: Flask User Salt Value
Format: "CHANGEME"
OSP_ALLOWREGISTRATION: Sets OSP to allow users to create accounts
Default: True
OSP_REQUIREVERIFICATION: Sets New OSP user accounts to verify their email addresses
Default: True
REDIS_HOST: Sets the Redis Instance IP/Hostname (REQUIRED)
REDIS_PORT: Sets the Redis Instance Port
Default: 6379
REDIS_PASSWORD: Sets the Redis Instance Password, if needed

#### Added in Beta 5a
Beta 5a will add additional Environment Variable to pre-configure OSP without needing to run the "First Run" Configuration
- OSP_ADMIN_USER
- OSP_ADMIN_EMAIL
- OSP_ADMIN_PASSWORD
- OSP_SERVER_NAME
- OSP_SERVER_PROTOCOL
- OSP_SERVER_ADDRESS
- OSP_SMTP_SEND_AS
- OSP_SMTP_SERVER
- OSP_SMTP_PORT
- OSP_SMTP_USER
- OSP_SMTP_PASSWORD
- OSP_SMTP_TLS
- OSP_SMTP_SSL
- OSP_ALLOW_RECORDING
- OSP_ALLOW_UPLOAD
- OSP_ADAPTIVE_STREAMING
- OSP_ALLOW_COMMENT
- OSP_DISPLAY_EMPTY

#### Recommended Volumes/Mount Points
- /var/www - Storage of Images, Streams, and Stored Video Files
- /usr/local/nginx/conf - Contains the NginX Configuration files which can be altered to suit your needs (HTTPS without something like Traefik)

## Database Setup

### Installation

#### Set Up MySQL
Prior to using MySQL with OSP the first time, do the following to configure OSP for full Unicode Support (UTF8MB4)
1. Install MySQL Server on Database Server or OSP Server
```bash
sudo apt-get install mysql-server
```
2. Copy the MySQL Configuration File in to MySQL
```bash
sudo cp /opt/osp/setup/mysql/mysqld.cnf /etc/mysql/my.cnf
```
3. Restart MySQL
```bash
sudo systemctl restart mysql
```
4. Open MySQL and create the OSP Database and User
```
sudo mysql
```
```mysql
CREATE DATABASE osp;
CREATE USER 'newuser'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON osp.* TO 'newuser'@'localhost';
```
5. Edit the OSP Configuration File to use MySQL
```
sudo vi /opt/osp/conf/config.py
```
From:
```
dbLocation="sqlite:///db/database.db"
```
To:
```
dbLocation = 'mysql+pymysql://username:password@localhost/osp?charset=utf8mb4'
```
6. Restart OSP
```
sudo systemctl restart osp.target
```
> Note: For Servers that have upgraded from versions prior to Beta 6, see https://wiki.openstreamingplatform.com/Install/Tweaks#database to convert from UTF8 to UTF8MB4 for Full Unicode Support

### Backup and Restore

#### Backup
System backups can be performed via making a backup copy of the /opt/osp/conf/config.py file and taking a SQL dump of the database using a tool like mysqldump
```
sudo mysqldump --databases osp > dump.sql
```

#### Restore

1. Copy the backup config.py file to /opt/osp/conf
2. Restore the SQL backup taken
```
mysql < dump.sql
```

### Migration

#### Moving from UTF8 to UTF8MB4 in MySQL
Installs prior to Beta 6 were not configured to fully use UTF8MB4 and may not be able to use the full Unicode set. To correct this issue, do the following:
1. Backup your existing Database per the proceedures above.
2. Shut down OSP
```
sudo systemctl stop osp.target
```
3. Open the MySQL Console
```
sudo mysql
```
4. Drop the OSP Database;
```
drop database osp;
```
5. Exit the MySQL Console
```
quit;
```
6. Follow the steps for Setting up a New MySQL install, starting at Step 2
7. On the Insital Setup Wizard, Restore your Database Per the Steps under Restore Above.

## Chat (XMPP)
Beginning with OSP v0.7.0, Chat has been moved to an XMPP based system using ejabberd. Channel chatrooms now maintain a temporary history and can be accessed by Guests, if configured.

### Installation

#### Single Server
By default, OSP will automatically install and configure XMPP components for use during install or upgrade to versions 0.7.0 or above. During the upgrade process, you will be prompted to enter the OSP Site Address. This address must match the OSP Site Address (Typically the OSP Fully Qualified Domain Name (FQDN) or IP Address of OSP) Failure to enter the correct address will cause the Chat system to not function properly.
If you must change your OSP Site Address, this change must also be made to the ejabberd.yml configuration file and ejabberd restarted.
You can find the ejabberd.yml file in ```/usr/local/ejabberd/conf/ejabberd.yml``` and edit the following lines:
*Line 17-19*
```yaml
hosts:
- localhost
- CHANGEME <---Your OSP Site Address
```
*Line 167-173*
```yaml
host_config:
"CHANGEME": <---Your OSP Site Address
auth_method:
- external
- anonymous
allow_multiple_connections: true
anonymous_protocol: login_anon
```
```bash
sudo systemctl restart ejabberd
```
OSP will also automatically set the ownership for each created OSP Channel and set the Channel Owner to Admin/Owner for the XMPP channel on start of the OSP service. If you have an issue with ownership, it is recommended to restart OSP to perform an XMPP Rebuild.

#### External Server
> Supported on versions >= 0.7.9
{.is-info}
Ejabberd can be configured to run an an external service. However, some manual changes must be made to allow it to operate with OSP properly.
To setup an external ejabberd server, do the following:
1. Install ejabberd on a separate server
```bash
sudo wget -O "/tmp/ejabberd-20.04-linux-x64.run" "https://www.process-one.net/downloads/downloads-action.php?file=/20.04/ejabberd-20.04-linux-x64.run"
chmod +x /tmp/ejabberd-20.04-linux-x64.run
/tmp/ejabberd-20.04-linux-x64.run ----unattendedmodeui none --mode unattended --prefix /usr/local/ejabberd --cluster 0
```
2. Create the conf directory and copy the ejabberd configuration yml, inetrc, and auth_osp.py from the OSP Repo to the directory
```bash
sudo mkdir /usr/local/ejabberd/conf
wget -O "/usr/local/ejabberd/conf/ejabberd.yml" "https://gitlab.com/osp-group/flask-nginx-rtmp-manager/-/raw/master/installs/ejabberd/setup/ejabberd.yml"
wget -O "/usr/local/ejabberd/conf/inetrc" "https://gitlab.com/osp-group/flask-nginx-rtmp-manager/-/raw/master/installs/ejabberd/setup/inetrc"
wget -O "/usr/local/ejabberd/conf/auth_osp.py" "https://gitlab.com/osp-group/flask-nginx-rtmp-manager/-/raw/master/installs/ejabberd/setup/auth_osp.py"
```
3. Edit the /usr/local/ejabberd/conf/ejabberd.yml file and update the fields based on your configuration
**Line 17-19**: Set CHANGEME to your OSP's FQDN
```
hosts:
- localhost
- OSP.example.com
```
**Line 43-53**: Change ip to "::"
```
port: 5443
ip: "::"
module: ejabberd_http
tls: true
request_handlers:
/admin: ejabberd_web_admin
/api: mod_http_api
/bosh: mod_bosh
/captcha: ejabberd_captcha
/upload: mod_http_upload
/ws: ejabberd_http_ws
```
**Line 55-65**: Change ip to "::"
```
port: 5280
ip: "::"
module: ejabberd_http
request_handlers:
/admin: ejabberd_web_admin
/api: mod_http_api
/bosh: mod_bosh
/captcha: ejabberd_captcha
/upload: mod_http_upload
/ws: ejabberd_http_ws
/.well-known/acme-challenge: ejabberd_acme
```
**Line 77-83**: Change ip to "::"
```
port: 4560
ip: "::"
module: ejabberd_xmlrpc
access_commands:
admin:
commands: all
options: []
```
**Line 87-96**: Add the IP Address to your OSP Instances in the ip block
```
acl:
local:
user_regexp: ""
loopback:
ip:
- 127.0.0.0/8
- ::1/128
- YOUR OSP IP HERE
admin:
user:
- "admin@localhost"
```
**Line 164**: Change the location of the auth_osp.py file to match below
```
extauth_program: "/usr/bin/python3 /usr/local/ejabberd/conf/auth_osp.py"
```
**Line 167-173**: Set CHANGEME to your OSP's FQDN
```
host_config:
"OSP.example.com":
auth_method:
- external
- anonymous
allow_multiple_connections: true
anonymous_protocol: login_anon
```
4. Install Python Requirements
```bash
sudo apt-get install python3-pip
sudo pip3 install requests
```
5. Edit the /usr/local/ejabberd/conf/auth_osp.py file
**Line 4-5**: Change the protocol and ospAPIServer values to match your OSP Instance
```
protocol = "http"
ospAPIServer = "OSP.example.com"
```
6. Copy the ejabberd SystemD file
```bash
sudo cp /usr/local/ejabberd/bin/ejabberd.service /etc/systemd/system/ejabberd.service
sudo systemctl daemon-reload
sudo systemctl enable ejabberd
sudo systemctl start ejabberd
```
7. Configure the local admin account with a password. Do not change the localadmin part
```bash
sudo /usr/local/ejabberd/bin/ejabberdctl register admin localhost YOURADMINPASSWORD
```
8. Install Nginx to reverse proxy the XMPP Bosh Port
```
sudo apt-get install nginx
```
9. Edit the default Nginx site file for the reverse proxy and add the following in the server directive block
```
sudo vi /etc/nginx/sites-available/default
```
```
location /http-bind/ { # BOSH XMPP-HTTP
proxy_pass http://localhost:5280/bosh;
proxy_set_header Host $host;
proxy_set_header X-Forwarded-For $remote_addr;
proxy_redirect off;
proxy_buffering off;
proxy_read_timeout 65s;
proxy_send_timeout 65s;
keepalive_timeout 65s;
tcp_nodelay on;
}
```
10. Restart the Nginx Service
```bash
sudo systemctl restart nginx
```
11. On the OSP Server, update the ejabberd admin password and add the ejabberdServer variable to the /opt/osp/conf/config.py file
```bash
sudo vi /opt/osp/conf/config.py
```
```python
# EJabberD Configuration
ejabberdAdmin = "admin"
ejabberdPass = "YOURADMINPASSWORD"
ejabberdHost = "localhost"
ejabberdServer = "ejabberd.example.com"
```
12. Restart the OSP Server
```bash
sudo systemctl restart osp.target
```

### Network Configuration
OSP's XMPP configuration requires the following open ports for chat to function:
- TCP/5222: Used for ejabberd Client to Server connections
- TCP/5269: Used for ejabberd Server to Server connections
- TCP/5443: External Server Jabber HTTPS-BOSH connection *External Server Only*
- TCP/5280: External Server Jabber HTTP-BOSH connection *External Server Only*
- TCP/4560: External Server XML-RPC Server Control *External Server Only*

### OSP Configuration
XMPP Channels are configured on a channel by channel basis. You can find the settings under Your Channels -> Chat
![2020-06-07_19_53_27-osp_demo_-_user_channels_page_and_11_more_pages_-_personal_-_microsoft​_edge.png](/2020-06-07_19_53_27-osp_demo_-_user_channels_page_and_11_more_pages_-_personal_-_microsoft​_edge.png)
Channel configuration allows you to define who is allowed to chat, how chat is managed, and who can manage it.
- **Room Title:** Name of Room, displayed to XMPP Chat Clients
- **Description:** Room description, displayed to XMPP Chat Clients
- **Moderated:** Only Users Identified as Participants may Chat
- **Allow guests to join room:** Allow Unauthenticated Guest Users to Join the Chat
- **Allow guests to chat:** Automatically set Unauthenticated Guest Users as Participants
You may also define automatic moderators for your channel in the Add Moderator section.

### Usage
The Chat Window is a basic display of conversations and moderation controls for users and admins. You can view who is in a channel, view their profile, or control basic functions such as ban lists or channel roles.
![2020-06-07_20_04_07-osp_demo_-_osp_demo_1_and_11_more_pages_-_personal_-_microsoft​_edge.png](/2020-06-07_20_04_07-osp_demo_-_osp_demo_1_and_11_more_pages_-_personal_-_microsoft​_edge.png)
All users are set as one the following roles:
- **Moderator**: Able to control the room and has access to all moderator controls
- **Participant**: Able to Chat in the room (ie: has voice)
- **Guest**: Able to view Chat in the room, but can not chat.
Any role changes made by a moderator are set as permanent and will remain on joining / leaving a room.

### User Options
By clicking on a username in chat or in the User List, users and moderators are displayed options targeting that user.
![2020-06-07_20_10_21-osp_demo_-_osp_demo_1_and_11_more_pages_-_personal_-_microsoft​_edge.png](/2020-06-07_20_10_21-osp_demo_-_osp_demo_1_and_11_more_pages_-_personal_-_microsoft​_edge.png)

### User Controls
- **Profile**: Opens a Popup that displays the User's Bio and any Channels, Streams, Videos, or Clips they may own
- **Mute**: Hides all chat from a user for your account. You will no longer see any messages from the user until you unmute them.

### Mod Controls
- **Kick**: Removes the user from the chatroom.
- **Ban**: Removes the user from the chatroom and flags their username as banned.
- **Change Role / Set as Moderator**: Sets the User to have Moderator Controls
- **Change Role / Set as Participant**: Sets the User to be a Participant (Able to Chat if Channel is set to Moderated)
- **Change Role / Set as Guest**: Sets the User to be a Guest (Can't Chat if Channel is set to Moderated)
- **Channel Voice Controls / Voice**: Temporarily grants Participant Status
- **Channel Voice Controls / Devoice**: Temporarily removes Participant Status

### Authentication
Each User maintains an XMPP token which is required to authenticate to the Chat Server. This is handled by OSP by default, but the token can also be used to authenticate using an XMPP client. To find you XMPP token, you can go to your user settings and copy the XMPP token at the bottom of the page.
![2020-06-07_20_23_32-osp_test_3_-_user_settings_and_12_more_pages_-_personal_-_microsoft​_edge.png](/2020-06-07_20_23_32-osp_test_3_-_user_settings_and_12_more_pages_-_personal_-_microsoft​_edge.png)
In addition to user XMPP tokens, each channel also maintains a XMPP token to be used when a Channel is set to be protected. In these instances, users may use the Channel XMPP Token to join the Chatroom using an external client.
![2020-06-07_20_25_05-osp_demo_-_user_channels_page_and_12_more_pages_-_personal_-_microsoft​_edge.png](/2020-06-07_20_25_05-osp_demo_-_user_channels_page_and_12_more_pages_-_personal_-_microsoft​_edge.png)

### Two Way Integration with Other Chat Clients
(Provided by djetaine on Discord)

Using Matterbridge, you can integrate your OSP Instance with multiple chat clients like Discord, IRC, Twitch, Telegram, etc.
Each platform should have its own "Bot" relay account that you will need to create.
For additional information and configuration instructions visit the [Matterbridge Wiki](https://github.com/42wim/matterbridge/wiki/) directly.

#### Installation - OSP
To facilitate certificate retrieval through the default nginx conf file will need to be modified.
If you cannot connect after you finish the installation, look at the ejabberd logs. In some instances you will need to manually create your cert files which can be done using the instructions under "Troubleshooting"
Create a backup folder and make a copy of your conf file
```
mkdir ~/backups
cp /usr/local/nginx/conf/nginx.conf ~/backups/nginx.conf
```
Open an editor to modify your conf
```
nano /usr/local/nginx/conf/nginx.conf
```
Add the following to your nginx conf file below the 443 server block
```
##Allow for ejabberd acme-challenge
server {
listen 80;
server_name conference.subdomain.domain.tld;
location / {
proxy_pass http://localhost:5280;
}
}
server {
listen 80;
server_name proxy.subdomain.domain.tld;
location / {
proxy_pass http://localhost:5280;
}
}
server {
listen 80;
server_name pubsub.subdomain.domain.tld;
location / {
proxy_pass http://localhost:5280;
}
}
```
Create DNS Records on your domain registrar for each of the subdomains required by ejabberd.
proxy.subdomain, pubsub.subdomain, conference.subdomain
Perform an nslookup or ping to very name resolution, restart osp and ejabberd then verify connectivity
```
sudo systemctl restart osp.target
sudo systemctl restart ejabberd
cat /usr/local/ejabberd/logs/ejabberd.log
```
If the certificate retrieval was successful, you will see success messages for the certificate. Don't worry about the local host warnings. If you see warnings for your FQDN, verify that your DNS entries are valid.
![enter image description here](https://i.imgur.com/yihxN8W.png)
Allow ejabberd traffic through your firewall. If you are hosting from home, be sure to port forward to your OSP host.
```
sudo ufw allow 5222/tcp
sudo ufw allow 5269/tcp
sudo ufw allow 5280/tcp
```
You can quickly test the external connectivity with an online xmpp client like conversejs
Get your xmpp username and password from your OSP profile settings page at the bottom, then login at [https://conversejs.org/fullscreen.html](https://conversejs.org/fullscreen.html)
If you can connect, move forward.

#### Install Matterbridge
Matterbridge will run on many different operating systems and container platforms. In this case we will focus on a digital ocean droplet running ubuntu minimal. See the github page for more information on other installations.
Get your instance of ubuntu up and running
Create Matterbridge user, download binaries, set permissions and create the directory
```
sudo adduser --system --no-create-home --group matterbridge
sudo wget https://github.com/42wim/matterbridge/releases/download/v1.22.3/matterbridge-1.22.3-linux-64bit -O /usr/bin/matterbridge
sudo chmod 755 /usr/bin/matterbridge
sudo mkdir /etc/matterbridge
```
You will now create your configuration file. There are a lot of integrations available but this document will focus on Twitch and Discord. More config help can be found in the Matterbridge Wiki
For discord, you will need to create a bot and get it's auth token. [Create a Discord Bot](https://github.com/42wim/matterbridge/wiki/Discord-bot-setup)
Get your ServerID and Channel ID by turning on developer mode then right clicking each to copy the ID.
For twitch, you can create a new "bot" user or user your own. Login to the account you wish to use as a relay, then go to https://twitchapps.com/tmi to get your oauth password. You need the whole thing, including the oauth:
![enter image description here](https://i.imgur.com/2qzKSH2.png)
Open an editor to create the config
```
sudo nano /etc/matterbridge/matterbridge.toml
```
You may copy this config file entering your own settings for FQDN, token, server, etc.
```
[discord.mydiscord]
Token="yourDiscordBotsToken"
Server="YourServerID"
RemoteNickFormat="{PROTOCOL}-**<{NICK}>** "
[irc.twitch]
#Add the oauth token here you got from https://twitchapps.com/tmi/
Password="oauth:SomeLettersAndNumbers"
Nick="YourTwitchBotsName"
Server="irc.twitch.tv:6667"
UseTLS=false
RemoteNickFormat="{PROTOCOL}-[{NICK}] "
[xmpp.myxmpp]
Server="fqdn.of.your.OSP.Server:5222"
#Jid your userid
Jid="OSPUserName@yourserver.tld"
Password="PasswordFromUserSettings"
Muc="conference.your.fqdn"
Nick="YourFriendlyUserName"
RemoteNickFormat="{PROTOCOL}-[{NICK}] "
[[gateway]]
name="gateway1"
enable=true
[[gateway.inout]]
account="irc.twitch"
channel="#YourTwitchChannel"
[[gateway.inout]]
account="xmpp.myxmpp"
channel="YourOSPChannelUID"
[[gateway.inout]]
account="discord.mydiscord"
channel="ChannelNameYouWantToSendTo"
```
Test your configuration by starting matterbridge.
```
/usr/bin/matterbridge -debug -conf /etc/matterbridge/matterbridge.toml
```
If all went well, create a service for matterbridge to run as.
```
sudo nano /etc/systemd/system/matterbridge.service
```
Paste the following and save the file
```
[Unit]
Description=matterbridge
After=network.target
[Service]
ExecStart=/usr/bin/matterbridge -conf /etc/matterbridge/matterbridge.toml
User=matterbridge
Group=matterbridge
[Install]
WantedBy=multi-user.target
```
Enable and run the service
```
sudo systemctl daemon-reload
sudo systemctl enable matterbridge
sudo systemctl start matterbridge
```
Set the service to run at startup
```
sudo systemctl enable matterbridge
```
You should now have a fully integrated chat with Twitch, OSP and Discord.

#### Troubleshooting
The two files that will be most important are the ejabberd log and the debug of the matterbridge service.
OSP Server
```
/usr/local/ejabberd/logs/ejabberd.log
```
Matterbridge Server re-run the matterbridge application with the -debug flag
```
/usr/bin/matterbridge -debug -conf /etc/matterbridge/matterbridge.toml
```
---

#### Manually configuring certificates if auto creation is not functioning
If the automated acme-challenge isnt working for one reason or another, you can create a cert and assign it manually. Run this command replacing subdomain.domain.tld with your fqdn
```
sudo certbot certonly --manual -d conference.subdomain.domain.tld -d proxy.subdomain.domain.tld -d pubsub.subdomain.domain.tld -d subdomain.domain.tld --agree-tos --no-bootstrap --manual-public-ip-logging-ok --preferred-challenges dns-01 --server https://acme-v02.api.letsencrypt.org/directory
```
Create txt records on your dns when asked. You will require a txt record for each subdomain.
Combine the full chain you create with the private key
```
cat etc/letsencrypt/live/yoursite/privkey.pem /etc/letsencrypt/live/yoursite/fullchain.pem > ~/combined.pem
```
Move your newly created combined pem file to a better location (something like /etc/ssl/ejabberd)
Uncomment the following lines in /usr/local/ejabberd/conf/ejabberd.yml
```
certfiles:
```
Add directly beneath
```
- /etc/ssl/ejabberd/combined.pem
```
Be SURE to line up your - /etc with the rest of the dashes in the yml file. YAML is very picky about spacing. It must tbe exact.

#### Let's Encrypt Setup
The focus of this guide will be to provide an example of how to setup SSL with LetsEncrypt and Certbot.
For this example we are using a default install of OSP on Ubuntu 20.04 (or 18.04) LTS
##### Step one, install Certbot
Install certbot (running with Nginx) as described at https://certbot.eff.org/instructions
Installion of certbot in short (for most systems) works with snap as follows:
```
# sudo snap install core; sudo snap refresh core
# sudo snap install --classic certbot
# sudo ln -s /snap/bin/certbot /usr/bin/certbot
```
Verify certbot is installed:
```
# certbot --version
certbot 1.13.0
```
##### Create a location for certbot verification outside of the actual webroot
```
# mkdir /var/certbot
# chmod 755 /var/certbot
```
Edit the OSP nginx config to use this location for the certbot verification by adding the following lines to /usr/local/nginx/conf/nginx.conf
```
location /.well-known/acme-challenge {
root /var/certbot;
}
```
These lines should go under your port 80 server, in my config I put them right below the line "include /usr/local/nginx/conf/locations/*.conf;"
```
# NGINX to HTTP Reverse Proxies
server {
include /usr/local/nginx/conf/custom/osp-custom-servers.conf;
# set client body size to 16M #
client_max_body_size 16M;
include /usr/local/nginx/conf/locations/*.conf;
location /.well-known/acme-challenge {
 root /var/certbot;
}
# redirect server error pages to the static page /50x.html
error_page 500 502 503 504 /50x.html;
location = /50x.html {
root html;
}
}
include /usr/local/nginx/conf/custom/osp-custom-serversredirect.conf;
```
##### Restart Nginx
```sudo systemctl restart nginx-osp```
##### Run certbot to request certs from LetsEncrypt
```
# sudo certbot certonly --webroot -w /var/certbot -d <domain>
```
This command will prompt you for a few pieces of information and then it will save your certs in /etc/letsencrypt/live/
```
- Congratulations! Your certificate and chain have been saved at:
/etc/letsencrypt/live/<domain>/fullchain.pem
Your key file has been saved at:
/etc/letsencrypt/live/<domain>/privkey.pem
Your cert will expire on <date>. To obtain a new or tweaked
version of this certificate in the future, simply run certbot
again. To non-interactively renew *all* of your certificates, run
"certbot renew"
```
##### Configure nginx-osp to use SSL and the certificates you have requested
Edit /usr/local/nginx/conf/custom/osp-custom-servers.conf and edit the section to similar to below:
Remember to change your domain name and certificate location to match the step above.
```
#listen 80 default_server;
### Comment Above and Uncomment/Edit Below for OSP-Proxy TLS ###
listen 443 ssl http2 default_server;
ssl_certificate /etc/letsencrypt/live/osp.example.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/osp.example.com/privkey.pem;
ssl_protocols TLSv1.2 TLSv1.3;
```
##### Configure nginx-osp to do http to https redirect
Uncomment all lines in /usr/local/nginx/conf/custom/osp-custom-serversredirect.conf to read as follows:
```
server {
listen 80;
server_name _;
return 301 https://$host$request_uri;
}
```
Restart nginx.osp
```
# sudo systemctl restart nginx-osp
```

## HAProxy Load Balancing

### Pre-requisites
This guide is designed for people running OSP Split server and **not** single server installations. This guide assumes that you currently have a working setup with at least 1 core server.
Tested working on Ubuntu 20.04 (LTS) on 2021.10.11. VPS Spec: 2GB RAM, 1 vCPU and 50GB Disk. Cloud Provider: Digital Ocean. For SSL installation your FQDN must be pointing at your HAProxy Server IP Address.
To Install, do the following:
```
apt-get update
apt-get upgrade
apt install -y haproxy
apt install -y certbot
```
After installing run haproxy -v to confirm installed and working as intended. You should get an output like:
HA-Proxy version 2.0.13-2ubuntu0.3 2021/08/27 - https://haproxy.org/

### Setup Config File
Once the install is done you can then configure the Config file
```
nano /etc/haproxy/haproxy.cfg
```
Under the defaults section, enter the following lines, replacing words (and the dashes) with your own information.
```
frontend --name to define frontend http--
# Define Port to Bind To and set the mode
bind :80
bind :::80
mode http
# Used to redirect HTTP Requests to HTTPS
# http-request redirect scheme https unless { ssl_fc }
# Enable this if you want to view stats
# stats uri /haproxy?stats
# Sets the default backend for servers
default_backend --name to define below backend (MUST MATCH)--
# Certbot SSL Installation
acl is_certbot path_beg /.well-known/acme-challenge/
use_backend backend-certbot if is_certbot
#frontend --name to define frontend https--
# bind :443 ssl crt /etc/haproxy/ssl/
# bind :::443 ssl crt /etc/haproxy/ssl/
# mode http
# ACL for detecting Let's Encrypt validtion requests
# acl is_certbot path_beg /.well-known/acme-challenge/
# use_backend backend-certbot if is_certbot
# default_backend --name to define below backend (MUST MATCH)--
backend --name to define below backend (MUST MATCH ABOVE default_backed)--
mode http
balance leastconn
server --yourservername-- --server internal or public ip--:80 check inter 5s rise 3 fall 2
backend backend-certbot
server letsencrypt 127.0.0.1:9080
```
Once that is done run
```
systemctl reload haproxy
```
The above config will get you running with HTTP. You must make sure that the default_backend under http and https match the backend name in the non backend-certbot section or haproxy wont start. You can change the server checks yourself but the above will check each core server every 5 seconds for a response. It it fails twice it will not use that server in the balancer.
If you want to be able to view your haproxy stats you can uncomment line 9 above and run
```
systemctl reload haproxy
```
You can then go to http://haproxyipaddress/fqdn/haproxy?stats or http://fqdn/haproxy?stats

### SSL Setup
In order to setup SSL Using LetsEncrypt your FQDN must be pointing to the public IP address of your haproxy server. You also need to have certbot installed.
Run the following, replacing mydomain.com with your FQDN and me@mydomain.com with your email address. You should get a message saying that your certificate and chain have been saved etc.
```
certbot certonly --standalone --preferred-challenges http --http-01-address 127.0.0.1 --http-01-port 9080 -d mydomain.com --email me@mydomain.com --agree-tos --non-interactive
```
We then need to combine those files into one for haproxy.
```
sudo nano /etc/haproxy/prepareLetsEncryptCertificates.sh
```
Then add the following:
```
#!/bin/bash
# Loop through all Let's Encrypt certificates
for CERTIFICATE in `find /etc/letsencrypt/live/* -type d`; do
CERTIFICATE=`basename $CERTIFICATE`
# Combine certificate and private key to single file
cat /etc/letsencrypt/live/$CERTIFICATE/fullchain.pem /etc/letsencrypt/live/$CERTIFICATE/privkey.pem > /etc/haproxy/ssl/$CERTIFICATE.pem
done
```
Create the SSL Directory
```
mkdir /etc/haproxy/ssl
```
Execute all the things!
```
chmod +x /etc/haproxy/prepareLetsEncryptCertificates.sh
sh /etc/haproxy/prepareLetsEncryptCertificates.sh
```
If the above has all gone well you should now be able to edit your haproxy config file and enable SSL by uncommenting the following lines in the config below (copied from above):
Line 7 - if you want to force SSL
Lines 16-19
Lines 21-23
```
frontend --name to define frontend http--
# Define Port to Bind To and set the mode
bind :80
bind :::80
mode http
# Used to redirect HTTP Requests to HTTPS
# http-request redirect scheme https unless { ssl_fc }
# Enable this if you want to view stats
# stats uri /haproxy?stats
# Sets the default backend for servers
default_backend --name to define below backend (MUST MATCH)--
# Certbot SSL Installation
acl is_certbot path_beg /.well-known/acme-challenge/
use_backend backend-certbot if is_certbot
#frontend --name to define frontend https--
# bind :443 ssl crt /etc/haproxy/ssl/
# bind :::443 ssl crt /etc/haproxy/ssl/
# mode http
# ACL for detecting Let's Encrypt validtion requests
# acl is_certbot path_beg /.well-known/acme-challenge/
# use_backend backend-certbot if is_certbot
# default_backend --name to define below backend (MUST MATCH)--
backend --name to define below backend (MUST MATCH ABOVE default_backed)--
mode http
balance leastconn
server --yourservername-- --server internal or public ip--:80 check inter 5s rise 3 fall 2
backend backend-certbot
server letsencrypt 127.0.0.1:9080
```

### Automatic Certificate Renewals and File Merging
Create a script to automate the certbot renewal and then merge the files and reload haproxy.
```
sudo nano /etc/haproxy/renewLetsEncryptCertificates.sh
```
Then Add:
```
#!/bin/bash
certbot renew --standalone --preferred-challenges http --http-01-address 127.0.0.1 --http-01-port 9080 --post-hook "/etc/haproxy/prepareLetsEncryptCertificates.sh && systemctl reload haproxy.service" --quiet
```
And make it executable:
```
chmod +x /etc/haproxy/renewLetsEncryptCertificates.sh
```
Create a cronjob to get the script to check for certificate renewals and run the certificate merge:
```
crontab -e
0 0 * * * /bin/sh /etc/haproxy/renewLetsEncryptCertificates.sh
```
Job done!

### Lock Down Stats Page
If you want the stats page to be active then haproxy have a good blog post on how to lock it down and also what all of the metrics mean below:
https://www.haproxy.com/blog/exploring-the-haproxy-stats-page/