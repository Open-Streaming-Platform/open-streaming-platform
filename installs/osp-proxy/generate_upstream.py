import os
import requests
from jinja2 import Environment, FileSystemLoader

from conf import config

# Pull List of RTMP Servers
r = requests.get(config.ospCoreAPI + '/apiv1/server/rtmp')
apiReturn = r.json()
rtmpServerList = apiReturn['results']

r = requests.get(config.ospCoreAPI + '/apiv1/server/')
apiReturn = r.json()
serverSettings = apiReturn['results']

for entry in rtmpServerList:
    if entry['address'] == '127.0.0.1' or entry['address'] == 'localhost':
        entry['address'] = serverSettings['siteAddress']
    entry['port'] = 5999

if hasattr(config, 'forceDestination'):
    if not any(d['address'] == config.forceDestination for d in rtmpServerList):
        if hasattr(config, 'forceDestinationType'):
            if config.forceDestinationType == 'edge':
                port = 0
            else:
                port = 5999
        else:
            port = 5999
        forcedDestination = {'address': config.forceDestination, 'port': port}
        rtmpServerList.append(forcedDestination)

templateList = []
for i in range(len(rtmpServerList)):
    if rtmpServerList[i] not in rtmpServerList[i + 1:]:
        templateList.append(rtmpServerList[i])
rtmpServerList = templateList

env = Environment(loader=FileSystemLoader('templates'))

# Render rtmp-location.conf
template = env.get_template('rtmp-location.conf')
output = template.render(rtmpServerList=rtmpServerList, serverSettings=serverSettings)

with open("/opt/osp-proxy/conf/rtmp-location.conf", "w") as fh:
    fh.write(output)

# Render rtmp-upstream.conf
template = env.get_template('rtmp-upstream.conf')
output = template.render(rtmpServerList=rtmpServerList)

with open("/opt/osp-proxy/conf/rtmp-upstream.conf", "w") as fh:
    fh.write(output)
