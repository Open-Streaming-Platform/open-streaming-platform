from flask import Flask, render_template, request, redirect
import redis

import requests
import os

from conf import config

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
rdis = redis.StrictRedis()
#----------------------------------------------------------------------------#
# Routes
#----------------------------------------------------------------------------#

location = {}

@app.route('/<endpoint>/<channelLocation>/<file>')
def home(endpoint,channelLocation,file):
    if rdis.exists(channelLocation) == False:
        header = {'X-Channel-ID': channelLocation}
        r = requests.get(config.ospCoreAPI + '/rtmpCheck', headers=header)
        rdis.set(channelLocation, r.headers['X_UpstreamHost'], 30)
        return redirect('/' + r.headers['X_UpstreamHost'] + '/' + endpoint + '/' + channelLocation + '/' + file)
    else:
        return redirect('/' + str(rdis.get(channelLocation).decode("utf-8")) + '/' + endpoint + '/' + channelLocation + '/' + file)

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=6999)
