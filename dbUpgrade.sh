#!/usr/bin/env bash

sudo service osp stop
python3 manage.py db migrate
python3 manage.py db upgrade
sudo service osp start