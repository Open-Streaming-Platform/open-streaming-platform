#!/usr/bin/env bash
cd /opt/osp
sudo systemctl stop osp.target
python3 manage.py db migrate
python3 manage.py db upgrade
sudo systemctl start osp.target