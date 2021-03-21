import os
import requests
from jinja2 import Environment, FileSystemLoader

from conf import config

# Check for a forced Destination
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

# Pull Server Info for Protocol Data and Local RTMP Servers
r = requests.get(config.ospCoreAPI + '/apiv1/server/')
apiReturn = r.json()
serverSettings = apiReturn['results']

# Pull List of RTMP Servers
r = requests.get(config.ospCoreAPI + '/apiv1/server/rtmp')
apiReturn = r.json()
rtmpServerList = apiReturn['results']

# Sets the RTMP External Port for Files
for entry in rtmpServerList:
    entry['port'] = 5999

# Verify there are no duplicate entries
templateList = []
for i in range(len(rtmpServerList)):
    if rtmpServerList[i] not in rtmpServerList[i + 1:]:
        templateList.append(rtmpServerList[i])
rtmpServerList = templateList

# Load Jinja2 Template Environment
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
