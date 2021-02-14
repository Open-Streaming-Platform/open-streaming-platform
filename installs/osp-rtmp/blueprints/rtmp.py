import subprocess
import requests

from flask import Blueprint, request, redirect, current_app, abort

from globals import globalvars

rtmp_bp = Blueprint('rtmp', __name__)

@rtmp_bp.route('/auth-key', methods=['POST'])
def streamkey_check():

    key = request.form['name']
    ipaddress = request.form['addr']

    # Execute Stage 1 RTMP Authentication
    stage1Request = requests.post(globalvars.apiLocation + "/apiv1/rtmp/stage1", data={'name':key, 'addr': ipaddress})
    if stage1Request.status_code == 200:
        stage1Response = stage1Request.json()
        if stage1Response['results']['success'] is True:
            channelLocation = stage1Response['results']['channelLoc']

            # Redirect based on API Response of Stream Type and Expected Stage 2 Handoff
            if stage1Response['results']['type'] == 'adaptive':
                return redirect('rtmp://127.0.0.1/stream-data-adapt/' + channelLocation, code=302)
            else:
                return redirect('rtmp://127.0.0.1/stream-data/' + channelLocation, code=302)
        else:
            returnMessage = stage1Response
            print(returnMessage)
            return abort(400)
    else:
        return abort(400)


@rtmp_bp.route('/auth-user', methods=['POST'])
def user_auth_check():
    key = request.form['name']
    ipaddress = request.form['addr']

    # Execute Stage 2 RTMP Authentication
    stage2Request = requests.post(globalvars.apiLocation + "/apiv1/rtmp/stage2", data={'name': key, 'addr': ipaddress})
    if stage2Request.status_code == 200:
        stage2Response = stage2Request.json()
        if stage2Response['results']['success'] is True:

            channelLocation = stage2Response['results']['channelLoc']
            inputLocation = "rtmp://127.0.0.1:1935/stream-data/" + channelLocation

            # Validate OSP's System Settings
            sysSettingsRequest = requests.get(globalvars.apiLocation + "/apiv1/server")
            if sysSettingsRequest.status_code == 200:
                sysSettingsResults = sysSettingsRequest.json()
            else:
                return abort(400)

            # Request a list of the Restream Destinations for a Channel via APIv1
            restreamDataRequest = requests.get(globalvars.apiLocation + "/apiv1/channel/" + channelLocation + "/restreams")
            if restreamDataRequest.status_code == 200:
                restreamDataResults = restreamDataRequest.json()
                globalvars.restreamSubprocesses[channelLocation] = []

                # Iterate Over Restream Destinations and Create ffmpeg Subprocess to Handle
                for destination in restreamDataResults['results']:
                    if destination['enabled'] is True:
                        p = subprocess.Popen(
                            ["ffmpeg", "-i", inputLocation, "-c", "copy", "-f", "flv", destination['url'], "-c:v",
                             "libx264", "-maxrate", str(sysSettingsResults['results']['restreamMaxBitRate']) + "k", "-bufsize",
                             "6000k", "-c:a", "aac", "-b:a", "160k", "-ac", "2"], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
                        globalvars.restreamSubprocesses[channelLocation].append(p)
            else:
                return abort(400)

            # Request List of OSP Edge Servers to Send a Restream To
            edgeNodeDataRequest = requests.get(globalvars.apiLocation + "/apiv1/server/edges")
            if edgeNodeDataRequest.status_code == 200:
                edgeNodeDataResults = edgeNodeDataRequest.json()
                globalvars.edgeRestreamSubprocesses[channelLocation] = []

                # Iterate Over Edge Node Results and Create ffmpeg Subprocess to Handle
                for node in edgeNodeDataResults['results']:
                    if node['active'] is True:
                        if node['address'] != sysSettingsResults['results']['siteAddress']:
                            subprocessConstructor = ["ffmpeg", "-i", inputLocation, "-c", "copy"]
                            subprocessConstructor.append("-f")
                            subprocessConstructor.append("flv")

                            # Sets Destination Endpoint based on System Adaptive Streaming Results
                            if sysSettingsResults['results']['adaptiveStreaming'] is True:
                                subprocessConstructor.append("rtmp://" + node['address'] + "/edge-data-adapt/" + channelLocation)
                            else:
                                subprocessConstructor.append("rtmp://" + node['address'] + "/edge-data/" + channelLocation)

                            p = subprocess.Popen(subprocessConstructor, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            globalvars.edgeRestreamSubprocesses[channelLocation].append(p)
                return 'OK'
            else:
                return abort(400)
        else:
            return abort(400)
    else:
        return abort(400)


@rtmp_bp.route('/auth-record', methods=['POST'])
def record_auth_check():
    key = request.form['name']

    # Execute Video Recording Start Check
    recStartRequest = requests.post(globalvars.apiLocation + "/apiv1/rtmp/reccheck", data={'name': key})
    if recStartRequest.status_code == 200:
        recStartResponse = recStartRequest.json()
        if recStartResponse['results']['success'] is True:
            return 'OK'
    return abort(400)

@rtmp_bp.route('/deauth-user', methods=['POST'])
def user_deauth_check():

    key = request.form['name']
    ipaddress = request.form['addr']

    # Execute Stream Close Request
    streamCloseRequest = requests.post(globalvars.apiLocation + "/apiv1/rtmp/streamclose", data={'name': key, 'addr': ipaddress})
    if streamCloseRequest.status_code == 200:
        streamCloseResponse = streamCloseRequest.json()
        if streamCloseResponse['results']['success'] is True:
            channelLocation = streamCloseResponse['results']['channelLoc']

            # End RTMP Restream Function
            if channelLocation in globalvars.restreamSubprocesses:
                for restream in globalvars.restreamSubprocesses[channelLocation]:
                    restream.kill()
                    try:
                        restream.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        restream.kill()
                        restream.wait(timeout=30)
            try:
                del globalvars.restreamSubprocesses[channelLocation]
            except KeyError:
                pass

            # End RTMP Edge Restreams
            if channelLocation in globalvars.edgeRestreamSubprocesses:
                for p in globalvars.edgeRestreamSubprocesses[channelLocation]:
                    p.kill()
                    try:
                        p.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        p.kill()
                        p.wait(timeout=30)
                try:
                    del globalvars.edgeRestreamSubprocesses[channelLocation]
                except KeyError:
                    pass

            return 'OK'
        else:
            return abort(400)
    return abort(400)

@rtmp_bp.route('/deauth-record', methods=['POST'])
def rec_Complete_handler():
    key = request.form['name']
    path = request.form['path']

    # Execute Recording Close Request
    recCloseRequest = requests.post(globalvars.apiLocation + "/apiv1/rtmp/recclose", data={'name': key, 'path': path})
    if recCloseRequest.status_code == 200:
        recCloseResponse = recCloseRequest.json()
        if recCloseResponse['results']['success'] is True:
            channelLocation = recCloseResponse['results']['channelLoc']
            return 'OK'
        else:
            abort(400)
    else:
        abort(400)