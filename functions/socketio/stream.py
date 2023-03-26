from flask_socketio import emit
from flask_security import current_user
from sqlalchemy import update

from classes.shared import db, socketio
from classes import Channel
from classes import Stream
from classes import settings


from functions import system
from functions import webhookFunc
from functions import templateFilters
from functions import xmpp
from functions import cachedDbCalls

from functions.scheduled_tasks import message_tasks

from app import r


@socketio.on("getViewerTotal")
def handle_viewer_total_request(streamData, room=None):
    channelLoc = str(streamData["data"])

    viewers = xmpp.getChannelCounts(channelLoc)
    channelQuery = cachedDbCalls.getChannelByLoc(channelLoc)
    if channelQuery != None:
        updateQuery = Channel.Channel.query.filter_by(channelLoc=channelLoc).update(dict(currentViewers=viewers))
        updateQuery = Stream.Stream.query.filter_by(linkedChannel=channelQuery.id, active=True, complete=False).update(dict(currentViewers=viewers))

    db.session.commit()
    db.session.close()
    if room is None:
        emit("viewerTotalResponse", {"data": str(viewers)})
    else:
        emit("viewerTotalResponse", {"data": str(viewers)}, room=room)
    return "OK"


@socketio.on("updateStreamData")
def updateStreamData(message):
    channelLoc = message["channel"]

    sysSettings = cachedDbCalls.getSystemSettings()
    channelQuery = cachedDbCalls.getChannelByLoc(channelLoc)
    if channelQuery != None:
        if channelQuery.owningUser == current_user.id:
            updateQuery = Stream.Stream.query.filter_by(linkedChannel=channelQuery.id, active=True, complete=False).update(dict(streamName=system.strip_html(message["name"]), topic=int(message["topic"])))
            db.session.commit()

            if channelQuery.imageLocation is None:
                channelImage = (
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/static/img/video-placeholder.jpg"
                )
            else:
                channelImage = (
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/images/"
                    + channelQuery.imageLocation
                )

            message_tasks.send_webhook.delay(
                channelQuery.id,
                4,
                channelname=channelQuery.channelName,
                channelurl=(
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/channel/"
                    + str(channelQuery.id)
                ),
                channeltopic=channelQuery.topic,
                channelimage=channelImage,
                streamer=templateFilters.get_userName(channelQuery.owningUser),
                channeldescription=str(channelQuery.description),
                streamname=system.strip_html(message["name"]),
                streamurl=(
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/view/"
                    + channelQuery.channelLoc
                ),
                streamtopic=templateFilters.get_topicName(int(message["topic"])),
                streamimage=(
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/stream-thumb/"
                    + channelQuery.channelLoc
                    + ".png"
                ),
            )
    db.session.commit()
    db.session.close()
    return "OK"
