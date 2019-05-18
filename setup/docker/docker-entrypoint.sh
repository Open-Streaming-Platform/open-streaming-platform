#!/bin/sh
cd /opt/osp
python3 manage.py db migrate
python3 manage.py db upgrade