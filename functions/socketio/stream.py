from flask_socketio import emit
from flask_security import current_user

from classes.shared import db, socketio
from classes import Channel
from classes import settings


from functions import system
from functions import webhookFunc
from functions import templateFilters

from app import r

@socketio.on('getViewerTotal')
def handle_viewer_total_request(streamData, room=None):
    channelLoc = str(streamData['data'])

    viewers = len(r.smembers(channelLoc + '-streamSIDList'))

    channelQuery = Channel.Channel.query.filter_by(channelLoc=channelLoc).first()
    if channelQuery is not None:
        channelQuery.currentViewers = viewers
        for stream in channelQuery.stream:
            stream.currentViewers = viewers
        db.session.commit()

    db.session.commit()
    db.session.close()
    if room is None:
        emit('viewerTotalResponse', {'data': str(viewers)})
    else:
        emit('viewerTotalResponse', {'data': str(viewers)}, room=room)
    return 'OK'

@socketio.on('updateStreamData')
def updateStreamData(message):
    channelLoc = message['channel']

    sysSettings = settings.settings.query.first()
    channelQuery = Channel.Channel.query.filter_by(channelLoc=channelLoc, owningUser=current_user.id).first()

    if channelQuery is not None:
        stream = channelQuery.stream[0]
        stream.streamName = system.strip_html(message['name'])
        stream.topic = int(message['topic'])
        db.session.commit()

        if channelQuery.imageLocation is None:
            channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
        else:
            channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + channelQuery.imageLocation)

        webhookFunc.runWebhook(channelQuery.id, 4, channelname=channelQuery.channelName,
                   channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(channelQuery.id)),
                   channeltopic=channelQuery.topic,
                   channelimage=channelImage, streamer=templateFilters.get_userName(channelQuery.owningUser),
                   channeldescription=str(channelQuery.description),
                   streamname=stream.streamName,
                   streamurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/view/" + channelQuery.channelLoc),
                   streamtopic=templateFilters.get_topicName(stream.topic),
                   streamimage=(sysSettings.siteProtocol + sysSettings.siteAddress + "/stream-thumb/" + channelQuery.channelLoc + ".png"))
        db.session.commit()
        db.session.close()
    db.session.commit()
    db.session.close()
    return 'OK'