#!/bin/sh

python3 /opt/osp-proxy/generate_upstream.py
systemctl reload nginx-osp