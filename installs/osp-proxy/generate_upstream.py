import os
import requests
from jinja2 import Environment, FileSystemLoader

from conf import config

r = requests.get(config.ospCoreAPI + '/apiv1/server/rtmp')
apiReturn = r.json()
rtmpServerList = apiReturn['results']

env = Environment(loader=FileSystemLoader('templates'))

# Render rtmp-location.conf
template = env.get_template('rtmp-location.conf')
output = template.render(rtmpServerList=rtmpServerList)

with open("/opt/osp-proxy/conf/rtmp-location.conf", "w") as fh:
    fh.write(output)

# Render rtmp-upstream.conf
template = env.get_template('rtmp-upstream.conf')
output = template.render(rtmpServerList=rtmpServerList)

with open("/opt/osp-proxy/conf/rtmp-upstream.conf", "w") as fh:
    fh.write(output)

