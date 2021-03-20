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
@app.route('/<endpoint>/<channelLocation>.m3u8')
def adaptive(endpoint,channelLocation):
    # Check if Force Destination Exists and Redirect to it, instead of querying OSP API
    if hasattr(config, 'forceDestination'):
        if config.forceDestinationType == "edge":
            endpoint = endpoint.replace('live','edge')
        return redirect('/' + forceDestination + '/' + endpoint + '/' + channelLocation + '.m3u8')
    else:
        # Check if Cached Redis RTMP Location Exists, If Not, Query API and Store the Result in Redis for a 30s Cache
        if rdis.exists(channelLocation) == False:
            header = {'X-Channel-ID': channelLocation}
            r = requests.get(config.ospCoreAPI + '/rtmpCheck', headers=header)
            rdis.set(channelLocation, r.headers['X_UpstreamHost'], 30)
            return redirect('/' + r.headers['X_UpstreamHost'] + '/' + endpoint + '/' + channelLocation + '/' + file)
        else:
            return redirect('/' + str(rdis.get(channelLocation).decode("utf-8")) + '/' + endpoint + '/' + channelLocation + '.m3u8')

@app.route('/<endpoint>/<channelLocation>/<file>')
def home(endpoint,channelLocation,file):
    channelParsed = channelLocation.split('_')[0]

    # Check if Force Destination Exists and Redirect to it, instead of querying OSP API
    if hasattr(config, 'forceDestination'):
        if config.forceDestinationType == "edge":
            endpoint = endpoint.replace('live','edge')
        return redirect('/' + forceDestination + '/' + endpoint + '/' + channelLocation + '/' + file)
    else:
        # Check if Cached Redis RTMP Location Exists, If Not, Query API and Store the Result in Redis for a 30s Cache
        if rdis.exists(channelParsed) == False:
            header = {'X-Channel-ID': channelParsed}
            r = requests.get(config.ospCoreAPI + '/rtmpCheck', headers=header)
            rdis.set(channelParsed, r.headers['X_UpstreamHost'], 30)
            return redirect('/' + r.headers['X_UpstreamHost'] + '/' + endpoint + '/' + channelLocation + '/' + file)
        else:
            return redirect('/' + str(rdis.get(channelParsed).decode("utf-8")) + '/' + endpoint + '/' + channelLocation + '/' + file)

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=6999)
