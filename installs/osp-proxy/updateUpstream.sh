#!/bin/sh

python3 /opt/osp-proxy/generate_upstream.sh
systemctl reload nginx