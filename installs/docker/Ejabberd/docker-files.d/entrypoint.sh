#!/usr/bin/env bash
cp -u -p /opt/ejabberd/run/ejabberd.yml /opt/ejabberd/conf/ejabberd.yml
cp -u -p /opt/ejabberd/run/auth_osp.py /opt/ejabberd/conf/auth_osp.py

# Configure ejabberd
export EJABBERD_DOMAIN
sed -i "s/CHANGEME/$EJABBERD_DOMAIN/g" /opt/ejabberd/conf/ejabberd.yml

#export EJABBERD_XMLRPC_ALLOWIP
#IFS="," read -a XMLRPCARRAY <<< $EJABBERD_XMLRPC_ALLOWIP
#XMLRPCSTRING=""
#for i in "${XMLRPCARRAY[@]}"
#do
#      XMLRPCSTRING+="      - $i\n"
#done
#sed -i "s/ALLOWXMLRPC/$XMLRPCSTRING/g" /opt/ejabberd/conf/ejabberd.yml

export OSP_API_PROTOCOL
export OSP_API_DOMAIN
export EJABBERD_PASSWORD

chown -R ejabberd:ejabberd /opt/ejabberd

supervisord --nodaemon --configuration /run/supervisord.conf
