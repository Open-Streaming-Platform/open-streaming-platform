#!/bin/sh
cd /opt/osp-proxy
python3 /opt/osp-proxy/generate_upstream.py
systemctl reload nginx-osp