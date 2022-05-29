# Troubleshooting
- OSP opens fine but when you try to stream to it, the stream never displays on the live channel page
- Check the Admin Settings under Site Protocol and Site Address. Incorrect values can cause the system to not pass the stream off properly to Nginx-RTMP.
- OSP doesn't open properly. The tv static error pages doesn't show and instead, a basic 500 error page is given
- Ensure the OSP service (sudo systemctl start osp.target) has been started. If it continues to fail, check the OSP logs:
```
cat /opt/osp/logs/osp-error.log
```
- OSP gives a 500 Internal Server Error when attempting to log in/post forms.
- This can happen when another reverse proxy is placed in front of OSP, usually Nginx. If the Edge Reverse proxy is not configured properly to forward the proxied address to OSP's Nginx install, it is seen as 127.0.0.1 to the inside reverse proxy. To correct, ensure you have the following configuration on your Edge Reverse Proxy (Per the [OSP Tweaks Page](https://wiki.openstreamingplatform.com/Install/Tweaks)):
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