from flask_security import current_user
from flask_socketio import join_room, leave_room, emit

from classes.shared import db, socketio
from classes import Channel
from classes import Stream
from classes import views

from functions import templateFilters
from functions import xmpp
from functions import cachedDbCalls
from functions.scheduled_tasks import message_tasks

from functions.socketio.stream import handle_viewer_total_request


@socketio.on("disconnect")
def disconnect():

    return "OK"


@socketio.on("newViewer")
def handle_new_viewer(streamData):
    channelLoc = str(streamData["data"])

    sysSettings = cachedDbCalls.getSystemSettings()

    requestedChannel = cachedDbCalls.getChannelByLoc(channelLoc)
    stream = (
        Stream.Stream.query.filter_by(active=True, streamKey=requestedChannel.streamKey)
        .with_entities(Stream.Stream.id)
        .first()
    )

    currentViewers = xmpp.getChannelCounts(requestedChannel.channelLoc)

    streamName = ""
    streamTopic = 0

    ChannelUpdateStatement = Channel.Channel.query.filter_by(
        channelLoc=channelLoc
    ).update(dict(currentViewers=currentViewers))

    if stream is not None:
        StreamUpdateStatement = Stream.Stream.query.filter_by(
            active=True, streamKey=requestedChannel.streamKey
        ).update(dict(currentViewers=currentViewers))

        streamName = stream.streamName
        streamTopic = stream.topic

    else:
        streamName = requestedChannel.channelName
        streamTopic = requestedChannel.topic

    if requestedChannel.imageLocation is None:
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
            + requestedChannel.imageLocation
        )

    join_room(streamData["data"])

    if current_user.is_authenticated:
        pictureLocation = current_user.pictureLocation
        if current_user.pictureLocation is None:
            pictureLocation = "/static/img/user2.png"
        else:
            pictureLocation = "/images/" + pictureLocation

        message_tasks.send_webhook.delay(
            requestedChannel.id,
            2,
            channelname=requestedChannel.channelName,
            channelurl=(
                sysSettings.siteProtocol
                + sysSettings.siteAddress
                + "/channel/"
                + str(requestedChannel.id)
            ),
            channeltopic=requestedChannel.topic,
            channelimage=channelImage,
            streamer=templateFilters.get_userName(requestedChannel.owningUser),
            channeldescription=str(requestedChannel.description),
            streamname=streamName,
            streamurl=(
                sysSettings.siteProtocol
                + sysSettings.siteAddress
                + "/view/"
                + requestedChannel.channelLoc
            ),
            streamtopic=templateFilters.get_topicName(streamTopic),
            streamimage=(
                sysSettings.siteProtocol
                + sysSettings.siteAddress
                + "/stream-thumb/"
                + requestedChannel.channelLoc
                + ".png"
            ),
            user=current_user.username,
            userpicture=(
                sysSettings.siteProtocol
                + sysSettings.siteAddress
                + str(pictureLocation)
            ),
        )
    else:
        message_tasks.send_webhook.delay(
            requestedChannel.id,
            2,
            channelname=requestedChannel.channelName,
            channelurl=(
                sysSettings.siteProtocol
                + sysSettings.siteAddress
                + "/channel/"
                + str(requestedChannel.id)
            ),
            channeltopic=requestedChannel.topic,
            channelimage=channelImage,
            streamer=templateFilters.get_userName(requestedChannel.owningUser),
            channeldescription=str(requestedChannel.description),
            streamname=streamName,
            streamurl=(
                sysSettings.siteProtocol
                + sysSettings.siteAddress
                + "/view/"
                + requestedChannel.channelLoc
            ),
            streamtopic=templateFilters.get_topicName(streamTopic),
            streamimage=(
                sysSettings.siteProtocol
                + sysSettings.siteAddress
                + "/stream-thumb/"
                + requestedChannel.channelLoc
                + ".png"
            ),
            user="Guest",
            userpicture=(
                sysSettings.siteProtocol
                + sysSettings.siteAddress
                + "/static/img/user2.png"
            ),
        )

    handle_viewer_total_request(streamData, room=streamData["data"])

    db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("addUserCount")
def handle_add_usercount(streamData):
    channelLoc = str(streamData["data"])

    requestedChannel = (
        Channel.Channel.query.filter_by(channelLoc=channelLoc)
        .with_entities(
            Channel.Channel.channelLoc,
            Channel.Channel.id,
            Channel.Channel.views,
            Channel.Channel.streamKey,
        )
        .first()
    )
    streamData = (
        Stream.Stream.query.filter_by(active=True, streamKey=requestedChannel.streamKey)
        .with_entities(Stream.Stream.id, Stream.Stream.totalViewers)
        .first()
    )

    ChannelUpdateStatement = Channel.Channel.query.filter_by(
        channelLoc=channelLoc
    ).update(dict(views=requestedChannel.views + 1))

    if streamData is not None:
        StreamUpdateStatement = Channel.Channel.query.filter_by(
            active=True, streamKey=requestedChannel.streamKey
        ).update(dict(totalViewers=streamData.totalViewers + 1))

    db.session.commit()

    newView = views.views(0, requestedChannel.id)
    db.session.add(newView)
    db.session.commit()

    db.session.close()
    return "OK"


@socketio.on("removeViewer")
def handle_leaving_viewer(streamData):
    channelLoc = str(streamData["data"])

    requestedChannel = (
        Channel.Channel.query.filter_by(channelLoc=channelLoc)
        .with_entities(
            Channel.Channel.channelLoc, Channel.Channel.id, Channel.Channel.views
        )
        .first()
    )
    stream = (
        Stream.Stream.query.filter_by(active=True, streamKey=requestedChannel.streamKey)
        .with_entities(Stream.Stream.id)
        .first()
    )

    currentViewers = xmpp.getChannelCounts(requestedChannel.channelLoc)

    if currentViewers < 0:
        ChannelUpdateStatement = Channel.Channel.query.filter_by(
            channelLoc=channelLoc
        ).update(dict(currentViewers=0))
    else:
        ChannelUpdateStatement = Channel.Channel.query.filter_by(
            channelLoc=channelLoc
        ).update(dict(currentViewers=currentViewers))

    if stream is not None:

        if currentViewers < 0:
            StreamUpdateStatement = Channel.Channel.query.filter_by(
                active=True, streamKey=requestedChannel.streamKey
            ).update(dict(currentViewers=0))

        else:
            StreamUpdateStatement = Channel.Channel.query.filter_by(
                active=True, streamKey=requestedChannel.streamKey
            ).update(dict(currentViewers=currentViewers))
    db.session.commit()

    leave_room(streamData["data"])

    handle_viewer_total_request(streamData, room=streamData["data"])

    db.session.close()
    return "OK"


@socketio.on("openPopup")
def handle_new_popup_viewer(streamData):
    join_room(streamData["data"])
    return "OK"


@socketio.on("closePopup")
def handle_leaving_popup_viewer(streamData):
    leave_room(streamData["data"])
    return "OK"
