from flask_security import current_user
from flask_socketio import emit
from sqlalchemy.sql.expression import func
import datetime

from classes.shared import db, socketio
from classes import Channel
from classes import webhook
from classes import settings
from classes import topics
from classes import RecordedVideo

from functions import webhookFunc
from functions import templateFilters
from functions import cachedDbCalls

from functions.scheduled_tasks import message_tasks


@socketio.on("submitWebhook")
def addChangeWebhook(message):

    invalidTriggers = [20]

    channelID = int(message["webhookChannelID"])
    channelQuery = cachedDbCalls.getChannel(channelID)
    if channelQuery is not None and channelQuery.owningUser == current_user.id:
        webhookName = message["webhookName"]
        webhookEndpoint = message["webhookEndpoint"]
        webhookTrigger = int(message["webhookTrigger"])
        webhookHeader = message["webhookHeader"]
        webhookPayload = message["webhookPayload"]
        webhookReqType = int(message["webhookReqType"])
        webhookInputAction = message["inputAction"]
        webhookInputID = message["webhookInputID"]

        if webhookInputAction == "new" and webhookTrigger not in invalidTriggers:
            newWebHook = webhook.webhook(
                webhookName,
                channelID,
                webhookEndpoint,
                webhookHeader,
                webhookPayload,
                webhookReqType,
                webhookTrigger,
            )
            db.session.add(newWebHook)
            db.session.commit()
            emit(
                "newWebhookAck",
                {
                    "webhookName": webhookName,
                    "requestURL": webhookEndpoint,
                    "requestHeader": webhookHeader,
                    "requestPayload": webhookPayload,
                    "requestType": webhookReqType,
                    "requestTrigger": webhookTrigger,
                    "requestID": newWebHook.id,
                    "channelID": channelID,
                },
                broadcast=False,
            )
        elif webhookInputAction == "edit" and webhookTrigger not in invalidTriggers:
            existingWebhookQuery = (
                webhook.webhook.query.filter_by(channelID=channelID, id=int(webhookInputID))
                .update(
                    dict(
                        name = webhookName,
                        endpointURL = webhookEndpoint,
                        requestHeader = webhookHeader,
                        requestPayload = webhookPayload,
                        requestType = webhookReqType,
                        requestTrigger = webhookTrigger
                    )
                )
            )

            emit(
                "changeWebhookAck",
                {
                    "webhookName": webhookName,
                    "requestURL": webhookEndpoint,
                    "requestHeader": webhookHeader,
                    "requestPayload": webhookPayload,
                    "requestType": webhookReqType,
                    "requestTrigger": webhookTrigger,
                    "requestID": existingWebhookQuery.id,
                    "channelID": channelID,
                },
                broadcast=False,
            )
    db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("deleteWebhook")
def deleteWebhook(message):
    webhookID = int(message["webhookID"])
    webhookQuery = webhook.webhook.query.filter_by(id=webhookID).with_entities(webhook.webhook.id, webhook.webhook.channelID).first()
    if webhookQuery is not None:
        channelQuery = cachedDbCalls.getChannel(webhookQuery.channelID)
        if channelQuery is not None:
            if channelQuery.owningUser is current_user.id:
                webhook.webhook.query.filter_by(id=webhookID).delete()
                db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("submitGlobalWebhook")
def addChangeGlobalWebhook(message):

    if current_user.has_role("Admin"):
        webhookName = message["webhookName"]
        webhookEndpoint = message["webhookEndpoint"]
        webhookTrigger = int(message["webhookTrigger"])
        webhookHeader = message["webhookHeader"]
        webhookPayload = message["webhookPayload"]
        webhookReqType = int(message["webhookReqType"])
        webhookInputAction = message["inputAction"]
        webhookInputID = message["webhookInputID"]

        if webhookInputAction == "new":
            newWebHook = webhook.globalWebhook(
                webhookName,
                webhookEndpoint,
                webhookHeader,
                webhookPayload,
                webhookReqType,
                webhookTrigger,
            )
            db.session.add(newWebHook)
            db.session.commit()
            emit(
                "newGlobalWebhookAck",
                {
                    "webhookName": webhookName,
                    "requestURL": webhookEndpoint,
                    "requestHeader": webhookHeader,
                    "requestPayload": webhookPayload,
                    "requestType": webhookReqType,
                    "requestTrigger": webhookTrigger,
                    "requestID": newWebHook.id,
                },
                broadcast=False,
            )
        elif webhookInputAction == "edit":
            existingWebhookQuery = (
                webhook.globalWebhook.query.filter_by(id=int(webhookInputID))
                .update(
                    dict(
                        name = webhookName,
                        endpointURL = webhookEndpoint,
                        requestHeader = webhookHeader,
                        requestPayload = webhookPayload,
                        requestType = webhookReqType,
                        requestTrigger = webhookTrigger
                    )
                )
            )

            emit(
                "changeGlobalWebhookAck",
                {
                    "webhookName": webhookName,
                    "requestURL": webhookEndpoint,
                    "requestHeader": webhookHeader,
                    "requestPayload": webhookPayload,
                    "requestType": webhookReqType,
                    "requestTrigger": webhookTrigger,
                    "requestID": existingWebhookQuery.id,
                },
                broadcast=False,
            )
    db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("deleteGlobalWebhook")
def deleteGlobalWebhook(message):
    webhookID = int(message["webhookID"])

    if current_user.has_role("Admin"):
        webhookQuery = webhook.globalWebhook.query.filter_by(id=webhookID).delete()
        db.session.delete(webhookQuery)
        db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("testWebhook")
def testWebhook(message):
    if current_user.is_authenticated:
        webhookID = int(message["webhookID"])
        webhookType = message["webhookType"]
        channelID = None

        if "channelID" in message:
            channelID = int(message["channelID"])

        sysSettings = cachedDbCalls.getSystemSettings()
        webhookQuery = None

        # Acquire a Channel to Test With
        channelQuery = None
        if channelID is not None:
            channelQuery = cachedDbCalls.getChannel(channelID)
        else:
            randomChannelIDQuery = Channel.Channel.query.order_by(func.rand()).with_entities(Channel.Channel.id).first()
            channelQuery = cachedDbCalls.getChannel(randomChannelIDQuery.id)

        # Acquire a Topic to Test With
        topic = topics.topics.query.order_by(func.rand()).with_entities(topics.topics.id).first()

        # Retrieve Current Picture
        pictureLocation = current_user.pictureLocation
        if current_user.pictureLocation is None:
            pictureLocation = "/static/img/user2.png"
        else:
            pictureLocation = "/images/" + pictureLocation

        if channelQuery is not None:

            # Prepare Channel Image
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

            if webhookType == "global":
                if current_user.has_role("Admin"):
                    webhookQuery = webhook.globalWebhook.query.filter_by(
                        id=webhookID
                    ).with_entities(webhook.globalWebhook.id).first()

            elif webhookType == "channel":
                webhookQuery = webhook.webhook.query.filter_by(id=webhookID).with_entities(webhook.webhook.id).first()
                if webhookQuery is not None:
                    if webhookQuery.channel.id != current_user.id:
                        webhookQuery = None

            results = message_tasks.test_webhook.delay(
                webhookType,
                webhookQuery.id,
                channelname=channelQuery.channelName,
                channelurl=(
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/channel/"
                    + str(channelQuery.id)
                ),
                channeltopic=templateFilters.get_topicName(channelQuery.topic),
                channelimage=channelImage,
                streamer=templateFilters.get_userName(channelQuery.owningUser),
                channeldescription=str(channelQuery.description),
                streamname="Testing Stream",
                streamurl=(
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/view/"
                    + channelQuery.channelLoc
                ),
                streamtopic=templateFilters.get_topicName(topic.id),
                streamimage=(
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/static/img/video-placeholder.jpg"
                ),
                user=current_user.username,
                userpicture=(
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + str(pictureLocation)
                ),
                videoname="Video Name",
                videodate=str(datetime.datetime.utcnow()),
                videodescription="Video Description",
                videotopic="Video Topic",
                videourl=(
                    sysSettings.siteProtocol + sysSettings.siteAddress + "/play/1"
                ),
                videothumbnail=(
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/static/img/video-placeholder.jpg"
                ),
                comment="This is just a test comment!",
                message="This is just a test message!",
            )
    db.session.commit()
    db.session.close()
    return "OK"
