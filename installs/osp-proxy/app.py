from flask import Flask, render_template, request, redirect, abort
import redis

from werkzeug.middleware.proxy_fix import ProxyFix

import requests
import os

from conf import config

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

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
        return redirect('/' + config.forceDestination + '/' + endpoint + '/' + channelLocation + '.m3u8')
    else:
        # Check if Cached Redis RTMP Location Exists, If Not, Query API and Store the Result in Redis for a 30s Cache
        if rdis.exists(channelLocation) == False:
            upstream = None
            header = {'X-Channel-ID': channelLocation}
            r = requests.get(config.ospCoreAPI + '/rtmpCheck', headers=header)
            if 'X_UpstreamHost' not in r.headers:
                abort(404)
            else:
                upstream = r.headers['X_UpstreamHost']
                if upstream == "127.0.0.1" or upstream == "localhost":
                    # Check API for server address
                    r = requests.get(config.ospCoreAPI + '/apiv1/server/')
                    apiReturn = r.json()
                    serverSettings = apiReturn['results']
                    upstream = serverSettings['siteAddress']
                rdis.set(channelLocation, upstream, 30)
            return redirect('/' + upstream + '/' + endpoint + '/' + channelLocation + 'm3u8')
        else:
            return redirect('/' + str(rdis.get(channelLocation).decode("utf-8")) + '/' + endpoint + '/' + channelLocation + '.m3u8')

@app.route('/<endpoint>/<channelLocation>/<file>')
def home(endpoint,channelLocation,file):
    channelParsed = channelLocation.split('_')[0]

    # Perform Auth Check for Encryption Keys
    fileExt = file[-3:]
    if fileExt == "key":
        if 'X-Token-Session' in request.headers:
            inboundHlsToken = request.headers.get('X-Token-Session')
            hlsToken = inboundHlsToken.split('_')
            clientIp = request.remote_addr
            authCheck = requests.post(config.ospCoreAPI + '/apiv1/rtmp/playbackauth', data={"username": hlsToken[0], "addr": clientIp, "name": channelLocation, "hash": hlsToken[1]})
            returnDataJson = authCheck.json()

            if returnDataJson['results'] is False or returnDataJson['results'] == 'False' or returnDataJson['results'] == 'false':
                abort(403)
        else:
            abort(403)

    # Check if Force Destination Exists and Redirect to it, instead of querying OSP API
    if hasattr(config, 'forceDestination'):
        if config.forceDestinationType == "edge":
            endpoint = endpoint.replace('live','edge')
        return redirect('/' + config.forceDestination + '/' + endpoint + '/' + channelLocation + '/' + file)
    else:
        # Check if Cached Redis RTMP Location Exists, If Not, Query API and Store the Result in Redis for a 30s Cache
        if rdis.exists(channelParsed) == False:
            upstream = None
            header = {'X-Channel-ID': channelParsed}
            r = requests.get(config.ospCoreAPI + '/rtmpCheck', headers=header)
            if 'X_UpstreamHost' not in r.headers:
                abort(404)
            else:
                upstream = r.headers['X_UpstreamHost']
                if upstream == "127.0.0.1" or upstream == "localhost":
                    # Check API for server address
                    r = requests.get(config.ospCoreAPI + '/apiv1/server/')
                    apiReturn = r.json()
                    serverSettings = apiReturn['results']
                    upstream = serverSettings['siteAddress']
            rdis.set(channelParsed, upstream, 30)
            return redirect('/' + upstream + '/' + endpoint + '/' + channelLocation + '/' + file)
        else:
            return redirect('/' + str(rdis.get(channelParsed).decode("utf-8")) + '/' + endpoint + '/' + channelLocation + '/' + file)

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=6999)
