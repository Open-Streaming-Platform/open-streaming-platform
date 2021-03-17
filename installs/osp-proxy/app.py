from flask import Flask, render_template, request, redirect

import requests
import os

from conf import config

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)

#----------------------------------------------------------------------------#
# Routes
#----------------------------------------------------------------------------#

location = {}

@app.route('/<endpoint>/<channelLocation>/<file>')
def home(endpoint,channelLocation,file):
    if channelLocation not in location:
        header = {'X-Channel-ID': channelLocation}
        r = requests.get(config.ospCoreAPI + '/rtmpCheck', headers=header)
        location[channelLocation] = r.headers['X_UpstreamHost']
        return redirect('/' + r.headers['X_UpstreamHost'] + '/' + endpoint + '/' + channelLocation + '/' + file)
    else:
        return redirect('/' + location[channelLocation] + '/' + endpoint + '/' + channelLocation + '/' + file)

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=6999)
