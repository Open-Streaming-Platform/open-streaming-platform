#!/usr/bin/env bash
cp -R -u -p /opt/osp/setup/nginx/*.conf /usr/local/nginx/conf/
cp -u -p /opt/osp/setup/nginx/mime.types /usr/local/nginx/conf/
cp -u -p /opt/osp/setup/config.py.dist /opt/osp/conf/config.py
chown -R www-data:www-data /opt/osp/conf/config.py
