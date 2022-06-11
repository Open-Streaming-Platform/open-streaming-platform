#!/usr/bin/env bash
cp -u -p /home/ejabberd/run/ejabberd.yml /home/ejabberd/conf/ejabberd.yml
cp -u -p /home/ejabberd/run/auth_osp.py /home/ejabberd/conf/auth_osp.py

# Configure ejabberd
export EJABBERD_DOMAIN
sed -i "s/CHANGEME/$EJABBERD_DOMAIN/g" /home/ejabberd/conf/ejabberd.yml

#export EJABBERD_XMLRPC_ALLOWIP
#IFS="," read -a XMLRPCARRAY <<< $EJABBERD_XMLRPC_ALLOWIP
#XMLRPCSTRING=""
#for i in "${XMLRPCARRAY[@]}"
#do
#      XMLRPCSTRING+="      - $i\n"
#done
#sed -i "s/ALLOWXMLRPC/$XMLRPCSTRING/g" /home/ejabberd/conf/ejabberd.yml

export OSP_API_PROTOCOL
export OSP_API_DOMAIN
export EJABBERD_PASSWORD

chown -R ejabberd:ejabberd /home/ejabberd

supervisord --nodaemon --configuration /run/supervisord.conf
