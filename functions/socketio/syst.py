import psutil
import os
import time
from flask import abort, current_app
from flask_socketio import emit
from flask_security import current_user
from sqlalchemy.sql.expression import func

from classes.shared import db, socketio, limiter
from classes import Sec
from classes import settings
from classes import RecordedVideo
from classes import Stream

from functions import system

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


@socketio.on('deleteStream')
def deleteActiveStream(message):
    if current_user.has_role('Admin'):
        streamID = int(message['streamID'])
        streamQuery = Stream.Stream.query.filter_by(id=streamID).first()
        if streamQuery is not None:
            pendingVideo = RecordedVideo.RecordedVideo.query.filter_by(pending=True, channelID=streamQuery.linkedChannel).all()
            for pending in pendingVideo:
                db.session.delete(pending)
            db.session.delete(streamQuery)
            db.session.commit()
            return 'OK'
        else:
            return abort(500)
    else:
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
