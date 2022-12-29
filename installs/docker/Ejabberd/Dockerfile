#FROM ejabberd/ecs:20.04
#FROM ugeek/ejabberd:arm64
#FROM sando38/docker-ejabberd-multiarch
FROM andrejunqueira33/ejabberd-new:1.0.0
#FROM ghcr.io/processone/ejabberd:master
MAINTAINER David Lockwood

# OSP Customized EJABBERD Docker Container
##########################################
# EJABBERD Container for use with a deployment of Open Streaming Platform (OSP)
#
# Environment Variables
# =====================
# EJABBERD_PASSWORD - admin@localhost Password for XMLRPC
# EJABBERD_DOMAIN - EJABBERD Chat Domain
# EJABBERD_XMLRPC_ALLOWIP - Comma Separated Value Set of Allowed - (ex: 10.1.20.1, 102.139.10.2) (Not Working Yet.  Set to 0.0.0.0/0 in yml)
# OSP_API_PROTOCOL - OSP API HTTP Protocol - Values: http or https
# OSP_API_DOMAIN - OSP API HTTP FQDN

ARG DEFAULT_TZ="ETC/UTC"

ARG DEFAULT_EJABBERD_DOMAIN=stream.example.com
ARG DEFAULT_EJABBERD_PASSWORD=CHANGEME
ARG DEFAULT_EJABBERD_XMLRPC_ALLOWIP=127.0.0.0/8
ARG DEFAULT_OSP_API_PROTOCOL=http
ARG DEFAULT_OSP_API_DOMAIN=stream.example.com

ENV OSP_EJABBED_VERSION=0.8.3
ENV EJABBERD_PASSWORD=$DEFAULT_EJABBERD_PASSWORD
ENV EJABBERD_DOMAIN=$DEFAULT_EJABBERD_DOMAIN
ENV EJABBERD_XMLRPC_ALLOWIP=$DEFAULT_EJABBERD_XMLRPC_ALLOWIP
ENV OSP_API_PROTOCOL=$DEFAULT_OSP_API_PROTOCOL
ENV OSP_API_DOMAIN=$DEFAULT_OSP_API_DOMAIN

USER root
RUN apk add --update python3 py3-pip
RUN pip3 install --upgrade pip
RUN pip install requests
RUN apk add --no-cache bash

COPY docker-files.d/entrypoint.sh /run/entrypoint.sh
RUN chmod +x /run/entrypoint.sh

RUN apk add supervisor
RUN mkdir -p /var/log/supervisor
COPY docker-files.d/supervisord.conf /run/supervisord.conf

USER ejabberd

RUN mkdir /home/ejabberd/run
COPY docker-files.d/ejabberd.yml /home/ejabberd/run/ejabberd.yml
COPY docker-files.d/auth_osp.py /home/ejabberd/run/auth_osp.py
COPY docker-files.d/inetrc /home/ejabberd/conf/inetrc

EXPOSE 5222
EXPOSE 5280

USER root
VOLUME ["/home/ejabberd/database"]

ENTRYPOINT ["/bin/sh","-c", "/run/entrypoint.sh"]
