import psutil
import os
import time
import shutil
import requests
from flask import abort, current_app
from flask_socketio import emit
from flask_security import current_user
from sqlalchemy.sql.expression import func
from urllib.parse import urlparse

from classes.shared import db, socketio, limiter
from classes import Sec
from classes import settings
from classes import RecordedVideo
from classes import Channel
from classes import Stream
from classes import views
from classes import apikey
from classes import panel

from functions import system
from functions import cachedDbCalls
from functions import topicsFunc
from functions import videoFunc
from functions import channelFunc

from app import user_datastore
from app import ejabberd

from conf import config

@socketio.on('checkUniqueUsername')
def deleteInvitedUser(message):
    newUsername = message['username']
    userQuery = Sec.User.query.filter(func.lower(Sec.User.username) == func.lower(newUsername)).first()
    if userQuery is None:
        emit('checkUniqueUsernameAck', {'results': str(1)}, broadcast=False)
    else:
        emit('checkUniqueUsernameAck', {'results': str(0)}, broadcast=False)
    db.session.commit()
    db.session.close()
    return 'OK'

@socketio.on('bulkAddRoles')
def bulkAddRoles(message):
    userList = message['users']
    role = message['role']
    if current_user.has_role('Admin'):
        for userID in userList:
            userQuery = Sec.User.query.filter_by(id=int(userID)).first()
            if userQuery is not None:
                user_datastore.add_role_to_user(userQuery, role)
        db.session.commit()
        db.session.close()
    return 'OK'

@socketio.on('deleteChannel')
def deleteChannelAdmin(message):
    channelID = int(message['channelID'])
    channelQuery = Channel.Channel.query.filter_by(id=channelID).first()
    if channelQuery is not None:
        if current_user.has_role('Admin') or channelQuery.owningUser == current_user.id:
            result = channelFunc.delete_channel(channelID)
            # Invalidate Channel Cache
            cachedDbCalls.invalidateChannelCache(channelID)
    return 'OK'

@socketio.on('deleteStream')
def deleteActiveStream(message):
    if current_user.has_role('Admin'):
        streamID = int(message['streamID'])
        streamQuery = Stream.Stream.query.filter_by(active=True, id=streamID).first()
        if streamQuery is not None:
            pendingVideo = RecordedVideo.RecordedVideo.query.filter_by(pending=True, channelID=streamQuery.linkedChannel).all()
            for pending in pendingVideo:
                db.session.delete(pending)
            db.session.delete(streamQuery)
            db.session.commit()
            db.session.close()
            return 'OK'
        else:
            db.session.commit()
            db.session.close()
            return abort(500)
    else:
        db.session.commit()
        db.session.close()
        return abort(401)

@socketio.on('deleteTopic')
def deleteTopic(message):
    if current_user.has_role('Admin'):
        topicID = int(message['topicID'])
        newTopicID = int(message['toTopicID'])
        topicsFunc.deleteTopic(topicID, newTopicID)
    return 'OK'

@socketio.on('getServerResources')
def get_resource_usage(message):
    cpuUsage = psutil.cpu_percent(interval=1)
    cpuLoad = psutil.getloadavg()
    cpuLoad = str(cpuLoad[0]) + ", " + str(cpuLoad[1]) + ", " + str(cpuLoad[2])
    memoryUsage = psutil.virtual_memory()[2]
    memoryUsageTotal = round(float(psutil.virtual_memory()[0])/1000000,2)
    memoryUsageAvailable = round(float(psutil.virtual_memory()[1])/1000000,2)
    diskUsage = psutil.disk_usage('/')[3]
    diskTotal = round(float(psutil.disk_usage('/')[0])/1000000,2)
    diskFree = round(float(psutil.disk_usage('/')[2]) / 1000000, 2)

    emit('serverResources', {'cpuUsage':str(cpuUsage), 'cpuLoad': cpuLoad, 'memoryUsage': memoryUsage, 'memoryUsageTotal': str(memoryUsageTotal), 'memoryUsageAvailable': str(memoryUsageAvailable), 'diskUsage': diskUsage, 'diskTotal': str(diskTotal), 'diskFree': str(diskFree)})
    return 'OK'

@socketio.on('testEmail')
def test_email(info):
    sysSettings = settings.settings.query.all()
    validTester = False
    if sysSettings == [] or sysSettings is None:
        validTester = True
    else:
        if current_user.has_role('Admin'):
            validTester = True
    if validTester is True:
        smtpServer = info['smtpServer']
        smtpPort = int(info['smtpPort'])
        smtpTLS = bool(info['smtpTLS'])
        smtpSSL = bool(info['smtpSSL'])
        smtpUsername = info['smtpUsername']
        smtpPassword = info['smtpPassword']
        smtpSender = info['smtpSender']
        smtpReceiver = info['smtpReceiver']

        results = system.sendTestEmail(smtpServer, smtpPort, smtpTLS, smtpSSL, smtpUsername, smtpPassword, smtpSender, smtpReceiver)
        db.session.close()
        emit('testEmailResults', {'results': str(results)}, broadcast=False)
        return 'OK'
    db.session.commit()
    db.session.close()
    return 'OK'

@socketio.on('cancelUpload')
def handle_videoupload_disconnect(videofilename):
    ospvideofilename = current_app.config['VIDEO_UPLOAD_TEMPFOLDER'] + '/' + str(videofilename['data'])
    thumbnailFilename = ospvideofilename + '.png'
    videoFilename = ospvideofilename + '.mp4'

    time.sleep(5)

    if os.path.exists(thumbnailFilename) and time.time() - os.stat(thumbnailFilename).st_mtime > 5:
            os.remove(thumbnailFilename)
    if os.path.exists(videoFilename) and time.time() - os.stat(videoFilename).st_mtime > 5:
            os.remove(videoFilename)

    return 'OK'

@socketio.on('updateDefaultRoles')
def update_default_roles(msg):
    if current_user.has_role('Admin'):

        UserRoleQuery = Sec.Role.query.filter_by(name="User").first()
        UserRoleQuery.default = True
        db.session.commit()

        hasStreamer = msg['streamer']
        StreamerRoleQuery = Sec.Role.query.filter_by(name="Streamer").first()
        StreamerRoleQuery.default = hasStreamer
        db.session.commit()

        hasRecorder = msg['recorder']
        RecorderRoleQuery = Sec.Role.query.filter_by(name="Recorder").first()
        RecorderRoleQuery.default = hasRecorder
        db.session.commit()

        hasUploader = msg['uploader']
        UploaderRoleQuery = Sec.Role.query.filter_by(name="Uploader").first()
        UploaderRoleQuery.default = hasUploader
        db.session.commit()
    db.session.close()
    return 'OK'

@socketio.on('disable2FA')
def disable_2fa(msg):
    if current_user.has_role('Admin'):
        userID = int(msg['userID'])
        userQuery = Sec.User.query.filter_by(id=userID).first()
        if userQuery is not None:
            userQuery.tf_primary_method = None
            userQuery.tf_totp_secret = None
            db.session.commit()
            system.newLog(1, "User " + current_user.username + " disabled 2FA for " + str(userQuery.username))
    db.session.close()
    return 'OK'

@socketio.on('admin_get_component_status')
def get_admin_component_status(msg):
    sysSettings = cachedDbCalls.getSystemSettings()
    if current_user.has_role('Admin'):
        component = msg['component']

        status = "Failed"

        if component == "osp_core":
            r = requests.get("http://127.0.0.1/apiv1/server/ping")
            if r.status_code == 200:
                response = r.json()
                if 'results' in response:
                    if response['results']['message'] == "Pong":
                        status = "OK"
                        message = "OSP-Core API Connection Successful"
        elif component == "osp_rtmp":
            rtmpServerListingQuery = settings.rtmpServer.query.filter_by(active=True).all()
            serverLength = len(rtmpServerListingQuery)
            workingServers = 0
            for rtmpServer in rtmpServerListingQuery:
                r = requests.get('http://' + rtmpServer.address + ":5099" + "/api/server/ping")
                if r.status_code == 200:
                    response = r.json()
                    if 'results' in response:
                        if response['results']['message'] == "pong":
                            workingServers = workingServers + 1
            if serverLength == workingServers:
                status = "OK"
                message = str(workingServers) + " RTMP Servers Online"
            elif workingServers > 0:
                status = "Problem"
                message = str(workingServers) + "/" + str(serverLength) + "RTMP Servers Online"
        elif component == "osp_proxy":
            if sysSettings.proxyFQDN != None and sysSettings.proxyFQDN != '':
                r = requests.get(sysSettings.siteProtocol + sysSettings.proxyFQDN + "/ping")
                if r.status_code == 200:
                    response = r.json()
                    if 'results' in response:
                        if response['results']['message'] == "pong":
                            status = "OK"
                            message = "OSP-Proxy Connection Successful"
                        else:
                            status = "Failed"
                            message = "OSP-Proxy Failed Check"
            else:
                status = "Problem"
                message = "No OSP-Proxy Configured"
        elif component == "osp_ejabberd_xmlrpc":
            results = ejabberd.check_password(config.ejabberdAdmin, config.ejabberdHost, config.ejabberdPass)
            if results['res'] == 0:
                status = "OK"
                message = "Ejabberd-XMLRPC Communication Confirmed"
            else:
                message = "Ejabberd-XMLRPC Error - Invalid Admin Password"
        elif component == "osp_ejabberd_chat":
            sysSettings = cachedDbCalls.getSystemSettings()

            from globals.globalvars import ejabberdServer, ejabberdServerHttpBindFQDN

            xmppserver = sysSettings.siteAddress
            if ejabberdServerHttpBindFQDN != None:
                xmppserver = ejabberdServerHttpBindFQDN
            elif ejabberdServer != "127.0.0.1" and ejabberdServer != "localhost":
                xmppserver = ejabberdServer

            r = requests.get(sysSettings.siteProtocol + xmppserver + '/http-bind')
            if r.status_code == 200:
                status = "OK"
                message = "BOSH-HTTP Reachable"
            else:
                message = "BOSH-HTTP Unreachable"
        elif component == "osp_database":
            try:
                sysSettings = settings.settings.query.first()
                if sysSettings != None:
                    status = "OK"
                    message = "DB Connection Successful"
                else:
                    status = "Problem"
                    message = "DB Connection Successful, but Settings Table Null"
            except:
                message = "DB Connection Failure"
        elif component == "osp_redis":
            from app import r
            try:
                r.ping()
                status = "OK"
                message = "Redis Ping Successful"
            except:
                message = "Redis Ping Failed"
        elif component == "osp_celery":
            from classes.shared import celery
            workerStatus = celery.control.ping()
            if workerStatus == []:
                message = "No OSP-Celery Instances Connected"
            else:
                if len(workerStatus) > 0:
                    verifiedWorker = 0
                    for worker in workerStatus:
                        for workerName in worker:
                            if 'ok' in worker[workerName]:
                                if worker[workerName]['ok'] == 'pong':
                                    verifiedWorker = verifiedWorker + 1
                    if len(workerStatus) == verifiedWorker:
                        status = "OK"
                        message = "All OSP-Celery Instances Online"
                    else:
                        status = "Problem"
                        message = str(verifiedWorker) + "/" + str(len(workerStatus)) + " OSP-Celery Workers Responded " + str(workerStatus)

        emit('admin_osp_component_status_update', {'component': component, 'status': status, 'message': message}, broadcast=False)

@socketio.on('deleteAPIKey')
def delete_apiKey(message):
    if current_user.is_authenticated:
        if 'keyId' in message:
            apiKeyID = int(message['keyId'])
            apiKeyQuery = apikey.apikey.query.filter_by(id=apiKeyID, userID=current_user.id).first()
            if apiKeyQuery != None:
                db.session.delete(apiKeyQuery)
                db.session.commit()
                return 'OK'
            else:
                db.session.commit()
                db.session.close()
    return 'OK'

@socketio.on('deletePanel')
def delete_global_panel(message):
    if current_user.is_authenticated:
        panelType = message['type']
        if panelType == 'channel':
            panelId = int(message['panelId'])
            panelQuery = panel.channelPanel.query.filter_by(id=panelId).first()
            if panelQuery != None:
                channelQuery = Channel.Channel.query.filter_by(id=panelQuery.channelId, owningUser=current_user.id).first()
                if channelQuery != None:
                    db.session.delete(panelQuery)
                    db.session.commit()
                else:
                    db.session.commit()
                    db.session.close()
            else:
                db.session.commit()
                db.session.close()
    return 'OK'

@socketio.on('deleteGlobalPanel')
def delete_global_panel(message):
    if current_user.is_authenticated:
        if current_user.has_role('Admin'):
            globalPanelId = int(message['globalPanelId'])
            panelQuery = panel.globalPanel.query.filter_by(id=globalPanelId).first()
            if panelQuery is not None:
                globalPanelMappingQuery = panel.panelMapping.query.filter_by(panelId=panelQuery.id).all()
                for panelMap in globalPanelMappingQuery:
                    db.session.delete(panelMap)
                    db.session.commit()
                db.session.delete(panelQuery)
                db.session.commit()
                return 'OK'
            else:
                db.session.commit()
                db.session.close()
    return 'OK'

@socketio.on('save_global_panel_mapping_front_page')
def save_global_panel_front_page(message):
    if current_user.is_authenticated:
        if current_user.has_role('Admin'):
            globalPanelListArray = message['globalPanelArray']
            existingFrontPageArray = panel.panelMapping.query.filter_by(pageName="root.main_page", panelType=0).all()
            for entry in existingFrontPageArray:
                db.session.delete(entry)
                db.session.commit()
            for entry in globalPanelListArray:
                position = globalPanelListArray.index(entry)
                panelId = entry.replace('front-panel-mapping-id-', '')
                newFrontPanelMapping = panel.panelMapping('root.main_page', 0, panelId, position)
                db.session.add(newFrontPanelMapping)
                db.session.commit()
    return 'OK'

@socketio.on('save_panel_mapping_page')
def save_panel_page(message):
    if current_user.is_authenticated:
        if 'channelId' in message:
            channelId = int(message['channelId'])
            channelQuery = Channel.Channel.query.filter_by(id=channelId, owningUser=current_user.id).first()
            if channelQuery != None:
                PanelListArray = message['panelArray']
                existingPageArray = panel.panelMapping.query.filter_by(pageName="liveview.view_page", panelLocationId=channelId, panelType=2).all()

                for entry in existingPageArray:
                    db.session.delete(entry)
                    db.session.commit()

                for entry in PanelListArray:
                    position = PanelListArray.index(entry)
                    panelId = entry.replace('panel-mapping-' + str(channelId) + '-id-', '')
                    newPanelMapping = panel.panelMapping('liveview.view_page', 2, panelId, position, panelLocationId=channelId)
                    db.session.add(newPanelMapping)
                    db.session.commit()
            else:
                db.session.commit()
                db.session.close()
    return 'OK'

@socketio.on('setGlobalPanelTarget')
def set_global_panel_target(message):
    if current_user.is_authenticated:
        if current_user.has_role('Admin'):
            panelId = message['panelId']
            targetId = message['targetId']
            panelQuery = panel.globalPanel.query.filter_by(id=panelId).first()
            if panelQuery is not None:
                panelQuery.target = targetId
            db.session.commit()
            db.session.close()
    return 'OK'

@socketio.on('addSocialNetwork')
def add_social_network(message):
    if current_user.is_authenticated:

        socialType = message['socialType']
        url = message['url']

        parsedURL = urlparse(url).geturl()

        socialQuery = Sec.UserSocial.query.filter_by(userID=current_user.id, socialType=socialType, url=parsedURL).first()

        if socialQuery is None:
            newSocial = Sec.UserSocial(current_user.id, socialType, parsedURL)
            db.session.add(newSocial)
            db.session.commit()
            NewSocialQuery = Sec.UserSocial.query.filter_by(userID=current_user.id, socialType=socialType, url=parsedURL).first()
            if NewSocialQuery is not None:
                emit('returnSocialNetwork', {'id': str(NewSocialQuery.id), 'socialType': NewSocialQuery.socialType, 'url': NewSocialQuery.url}, broadcast=False)
        db.session.close()
    return 'OK'

@socketio.on('removeSocialNetwork')
def delete_social_network(message):
    if current_user.is_authenticated:
        socialQuery = Sec.UserSocial.query.filter_by(id=int(message['id'])).first()
        if socialQuery is not None:
            db.session.delete(socialQuery)
            db.session.commit()
        db.session.close()
    return 'OK'