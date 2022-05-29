# Tweaks

## Network

### TCP Tweaks
Starting with 0.7.2, OSP has a sysctl.d tweak to optimize TCP connections in Linux where there may be problems causing packetloss and bufferbloat
To Install, do the following:
```
sudo cp /opt/osp/setup/sysctl.d/30-osp-tcp.conf /etc/sysctl.d/
sudo sysctl -p /etc/sysctl.d/30-osp-tcp.conf
```

## Reverse Proxy
In some instances where you are using OSP in a shared environment (Docker or other shared services) you may be required to have a reverse proxy in front of OSP. In these instances, some additional configuration may be required for your Edge Reverse Proxy.

### Traefik
The Traefik reverse proxy should work out of the box for port 80 and 443. However, the RTMP port must have direct access for OSP to Stream properly.

### Nginx
For Nginx to work properly as a reverse proxy in front of the OSP stack, you must ensure Nginx is setting the proper headers to forward to OSP's Nginx. When setting the location going to OSP, ensure that the following settings are set for the Edge Reverse Proxy:
```
location / {
proxy_pass http://IPADDRESS;
proxy_redirect off;
proxy_set_header Host $host:$server_port;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
}
location /socket.io {
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header Host $host;
proxy_set_header X-NginX-Proxy true;
# prevents 502 bad gateway error
 proxy_buffers 8 32k;
proxy_buffer_size 64k;
proxy_redirect off;
# enables WS support
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_pass http://IPADDRESS/socket.io;
}
```

## Database

### Caching
MySQL and associated DBs can be configured to Cache SQL Queries:
> Warning: Newer versions of MySQL have depricated the below commands and can cause MySQL to not load
{.is-warning}
Add/Adjust the following lines in your mysqld.cnf
```
query_cache_limit = 1M
query_cache_type = 1
query_cache_size = 16M
```

### Max Connections
In larger instances, it is recommended to increate the number of allowed database connections by editing the database configuration file:

#### MySQL
1. Edit the /etc/mysql/msql.conf.d/mysqld.cnf
```
vi /etc/mysql/msql.conf.d/mysqld.cnf
```
2. Edit the line max_connections and increase to a larger number
```
max_connections = 100000
```
3. Restart the DB
```
sudo systemctl restart mysql
```

#### MariaDB
1. Edit the /etc/mysql/mariadb.conf.d/50-server.cnf
```
vi /etc/mysql/mariadb.conf.d/50-server.cnf
```
2. Edit the line max_connections and increase to a larger number
```
max_connections = 100000
```
3. Restart the DB
```
sudo systemctl restart mariadb
```

## Transcoding Tweaks

### Use Hardware Accelerated Transcoding

#### NVIDIA GPU Transcoding (Ubuntu Server)
(As Submitted by multi.flexi on 18/6/2021)
1: Install Dependencies (not sure if all necessary)
```
sudo apt install ladspa-sdk-dev libaom-dev libass-dev libbluray-dev libbs2b-dev libcaca-dev libcdio-paranoia-dev libcodec2-dev flite1-dev libfribidi-dev libgme-dev libgsm1-dev libjack-dev libmp3lame-dev libmysofa-dev libopenmpt-dev libopus-dev libpulse-dev librsvg2-dev librubberband-dev libshine-dev libsnappy-dev libsoxr-dev libspeex-dev libssh-dev libtheora-dev libtwolame-dev libvidstab-dev libvorbis-dev libvpx-dev libwavpack-dev libwebp-dev libx264-dev libx265-dev libxml2-dev libxvidcore-dev libzmq3-dev libzvbi-dev libomxil-bellagio-dev libopenal-dev libsdl2-dev libdc1394-22-dev libchromaprint-dev frei0r-plugins-dev libfreetype6-dev build-essential nasm yasm libgnutls28-dev liblilv-dev libdrm-dev libopenjp2-7-dev
```
2: Install NVIDIA Driver Set
```
sudo apt install --no-install-recommends nvidia-driver-460
```
3: Install NVIDIA CUDA Toolkit
```
sudo apt install nvidia-cuda-toolkit
```
4: Remove Existing FFmpeg
```
sudo apt remove ffmpeg
```
5: Download and Compile FFmpeg nVidia headers
```
cd /tmp
git clone https://git.videolan.org/git/ffmpeg/nv-codec-headers.git
cd nv-codec-headers
make && sudo make install
```
6: Download and Compile FFmpeg
```
cd /tmp
wget -O ffmpeg-snapshot.tar.bz2 https://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2 && tar xjvf ffmpeg-snapshot.tar.bz2
cd ffmpeg
./configure --prefix=/usr --extra-version='0york0~20.04' --toolchain=hardened --libdir=/usr/lib/x86_64-linux-gnu --incdir=/usr/include/x86_64-linux-gnu --arch=amd64 --enable-gpl --disable-stripping --enable-gnutls --enable-ladspa --enable-libaom --enable-libass --enable-libbluray --enable-libbs2b --enable-libcaca --enable-libcdio --enable-libcodec2 --enable-libflite --enable-libfontconfig --enable-libfreetype --enable-libfribidi --enable-libgme --enable-libgsm --enable-libjack --enable-libmp3lame --enable-libmysofa --enable-libopenjpeg --enable-libopenmpt --enable-libopus --enable-libpulse --enable-librsvg --enable-librubberband --enable-libshine --enable-libsnappy --enable-libsoxr --enable-libspeex --enable-libssh --enable-libtheora --enable-libtwolame --enable-libvidstab --enable-libvorbis --enable-libvpx --enable-libwebp --enable-libx265 --enable-libxml2 --enable-libxvid --enable-libzmq --enable-libzvbi --enable-lv2 --enable-omx --enable-openal --enable-opengl --enable-sdl2 --enable-libdc1394 --enable-libdrm --enable-chromaprint --enable-frei0r --enable-libx264 --enable-shared --enable-cuda --enable-cuvid --enable-nvenc --enable-nonfree --enable-libnpp
make -j
sudo make install
```
7: Edit the osp-rtmp.conf file to transpile on the GPU
- Under application stream-data-adapt and streamrec-data-adapt:
```
exec ffmpeg -y -vsync 0 -hwaccel cuda -hwaccel_output_format cuda -i rtmp://127.0.0.1:1935/live/$name
-c:v h264_nvenc -c:a aac -b:v 768k -b:a 96k -vf "scale_npp=852:trunc(ow/a/2)*2" -preset llhq -tune ll -zerolatency 1 -f flv rtmp://localhost:1935/show/$name_480
-c:v h264_nvenc -c:a aac -b:v 1920k -b:a 128k -vf "scale_npp=1280:trunc(ow/a/2)*2" -preset llhq -tune ll -zerolatency 1 -f flv rtmp://localhost:1935/show/$name_720
-c copy -f flv rtmp://localhost:1935/show/$name_src;
```
8: Restart Nginx
```
service nginx-osp restart
```

### Storing transcoded data in a RAM-Disk
(Written by who, 30/7/2021)
> Warning: This is only recommended, if you are having 16GB (or more) RAM in your server.
{.is-warning}
Since the files from the transcoding process are written and read quite often to/from your disk and are not needed anymore after a reboot, those files can be stored in a RAM-Disk (tmpfs). Basically this is good for your disk health and improves the read and write speed.
You just have to add a new line to ```/etc/fstab``` with the following command:
```
sudo echo "tmpfs /var/www/live-adapt tmpfs defaults,mode=0755,uid=$(id -u www-data),gid=$(id -g www-data) 0 0" >> /etc/fstab
```
After that, you have to make sure to mount your new tmpfs and restart the nginx afterwards.
```
sudo mount -a
sudo systemctl restart nginx-osp.service
```
The new filesystem should now occur, if you execute ```df -h -t tmpfs```.

## Scaling

### Using Digital Ocean Spaces
(Written by djetaine)
Digital Ocean is a cloud provider that has multiple offerings including k8s, docker, standard vps but most importantly, s3 compatible object storage called Spaces. This guide will show you how to use DO Spaces to store and deliver OSP video content

#### Prerequisites:
- Create an account with digital ocean and create a project.
- This is a paid service. While DO does offer (at the time of this writing) 100 dollars of free credit for 30 days, it will eventually cost you money. Pay attention to your statistics and plan accordingly.
- A DO Space in your closest datacenter.
- DO does offer a CDN you can use in front of your Space. This document does not currently cover content delivery networks.
- Digital Ocean API Keys
- This assumes a new installation. If you already have videos, there will be more work to do and you will need to copy the files to your space and run the mount command with the ```-o nonempty flag``` at the end
- Make a backup of your /var/www/videos directory
- Actually make a backup of your /var/www/videos directory

#### Setting up your server to accept the space
- Getting your Digital Ocean API Keys
- Click "API" at the bottom of the nav pan on the left in your DO Administrative Console.
- Generate a space access key [key] and a personal access token [token] . Save this somewhere you can access them easily for copy and paste
- Mounting an s3 compatible bucket requires s3fs to be installed on your OSP server
```
sudo apt-get update
sudo apt-get install s3fs
```
- Create your password file. Your key and token here are what you obtained from the API. Enter these without the <>
Example: ```echo AFRKWOTYASFKNAF:dahAuyaf7856aADha7863haDAD86568 > ~/.passwd-s3fs```
```echo <key>:<token> > ~/.passwd-s3fs```
- Set the permissions so only the owner can read/write this file
```chmod 600 ~/.passwd-s3fs```
- Edit the fuse configuration to allow access by non root users to files created through the DO web UI if needed.
``` sudo nano /etc/fuse.conf```
uncomment (remove the #) from the following line:
```user_allow_other```
- Find the id of www-data for use in mounting as a writable user
```id```
Find the user named www-data and note the uid and gid.
example output: ```uid=1234(www-data) gid=1234(www-data) groups=1234(user)```
So our uid and gid are 1234 here.
- Mount the space to the videos folder using your space name that you created when you made your space, your uid, gid and space_region
```s3fs <space_name> /var/www/videos -o url=https://<space_region>.digitaloceanspaces.com -o use_cache=/tmp -o allow_other -o use_path_request_style -o uid=<UID> -o gid=GID```
Example using the information we got before:
```s3fs OSPVideos /var/www/videos -o url=https://nyc3.digitaloceanspaces.com -o use_cache=/tmp -o allow_other -o use_path_request_style -o uid=1234 -o gid=1234```
- Verify that the mount was successful
```mount```
At the bottom of the output you should see your space listed as an s3fs mount.

#### Troubleshooting
- You receive a message about the directory not being empty. See the prereqs above.
- The command runs but it does not mount and you see no error:
- Verify that you do not have an additional mount with the same name (possible in error). If you do, unmount it with ```umount /var/www/videos```
- Check your syslog for credential validation errors
- Syslog says "Invalid Credentials
- ```cat ~/.passwd-s3fs``` this should have a single line in it with your key:your token with no spaces
- ```cat /etc/fuse.conf``` verify you actually removed the # in front of user_allow_other
- Last resort, recreate your space access and personal keys from Digital Ocean on the Spaces admin panel. Once recreated, delete/recreate the .passwd-s3fs file