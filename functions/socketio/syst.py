import psutil
import os
import time
import shutil
import requests
from flask import abort, current_app
from flask_socketio import emit
from flask_security import current_user
from sqlalchemy.sql.expression import func

from classes.shared import db, socketio, limiter
from classes import Sec
from classes import settings
from classes import RecordedVideo
from classes import Channel
from classes import Stream
from classes import views

from functions import system
from functions import cachedDbCalls

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
            for vid in channelQuery.recordedVideo:
                for upvote in vid.upvotes:
                    db.session.delete(upvote)
                vidComments = vid.comments
                for comment in vidComments:
                    db.session.delete(comment)
                vidViews = views.views.query.filter_by(viewType=1, itemID=vid.id)
                for view in vidViews:
                    db.session.delete(view)
                for clip in vid.clips:
                    db.session.delete(clip)

                db.session.delete(vid)

            for upvote in channelQuery.upvotes:
                db.session.delete(upvote)
            for inviteCode in channelQuery.inviteCodes:
                db.session.delete(inviteCode)
            for viewer in channelQuery.invitedViewers:
                db.session.delete(viewer)
            for sub in channelQuery.subscriptions:
                db.session.delete(sub)
            for hook in channelQuery.webhooks:
                db.session.delete(hook)
            for sticker in channelQuery.chatStickers:
                db.session.delete(sticker)

            stickerFolder = '/var/www/images/stickers/' + channelQuery.channelLoc + '/'
            shutil.rmtree(stickerFolder, ignore_errors=True)

            filePath = globalvars.videoRoot + channelQuery.channelLoc

            if filePath != globalvars.videoRoot:
                shutil.rmtree(filePath, ignore_errors=True)

            from app import ejabberd
            sysSettings = cachedDbCalls.getSystemSettings()
            ejabberd.destroy_room(channelQuery.channelLoc, 'conference.' + sysSettings.siteAddress)

            system.newLog(1, "User " + current_user.username + " deleted Channel " + str(channelQuery.id))
            db.session.delete(channelQuery)
            db.session.commit()
    db.session.close()
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
    if current_user.has_role('Admin'):
        component = msg['component']

        status = "Failed"

        if component == "osp_rtmp":
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

        emit('admin_osp_component_status_update', {'component': component, 'status': status, 'message': message}, broadcast=False)

