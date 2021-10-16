from flask_security import current_user
from flask_socketio import emit
from sqlalchemy.sql.expression import func

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

@socketio.on('submitWebhook')
def addChangeWebhook(message):

    invalidTriggers = [20]

    channelID = int(message['webhookChannelID'])

    channelQuery = Channel.Channel.query.filter_by(id=channelID, owningUser=current_user.id).first()
    if channelQuery is not None:
        webhookName = message['webhookName']
        webhookEndpoint = message['webhookEndpoint']
        webhookTrigger = int(message['webhookTrigger'])
        webhookHeader = message['webhookHeader']
        webhookPayload = message['webhookPayload']
        webhookReqType = int(message['webhookReqType'])
        webhookInputAction = message['inputAction']
        webhookInputID = message['webhookInputID']

        if webhookInputAction == 'new' and webhookTrigger not in invalidTriggers:
            newWebHook = webhook.webhook(webhookName, channelID, webhookEndpoint, webhookHeader, webhookPayload, webhookReqType, webhookTrigger)
            db.session.add(newWebHook)
            db.session.commit()
            emit('newWebhookAck', {'webhookName': webhookName, 'requestURL':webhookEndpoint, 'requestHeader':webhookHeader, 'requestPayload':webhookPayload, 'requestType':webhookReqType, 'requestTrigger':webhookTrigger, 'requestID':newWebHook.id, 'channelID':channelID}, broadcast=False)
        elif webhookInputAction == 'edit' and webhookTrigger not in invalidTriggers:
            existingWebhookQuery = webhook.webhook.query.filter_by(channelID=channelID, id=int(webhookInputID)).first()
            if existingWebhookQuery is not None:
                existingWebhookQuery.name = webhookName
                existingWebhookQuery.endpointURL = webhookEndpoint
                existingWebhookQuery.requestHeader = webhookHeader
                existingWebhookQuery.requestPayload = webhookPayload
                existingWebhookQuery.requestType = webhookReqType
                existingWebhookQuery.requestTrigger = webhookTrigger
                emit('changeWebhookAck', {'webhookName': webhookName, 'requestURL': webhookEndpoint, 'requestHeader': webhookHeader, 'requestPayload': webhookPayload, 'requestType': webhookReqType, 'requestTrigger': webhookTrigger, 'requestID': existingWebhookQuery.id, 'channelID': channelID}, broadcast=False)
    db.session.commit()
    db.session.close()
    return 'OK'

@socketio.on('deleteWebhook')
def deleteWebhook(message):
    webhookID = int(message['webhookID'])
    webhookQuery = webhook.webhook.query.filter_by(id=webhookID).first()

    if webhookQuery is not None:
        channelQuery = webhookQuery.channel
        if channelQuery is not None:
            if channelQuery.owningUser is current_user.id:
                db.session.delete(webhookQuery)
                db.session.commit()
    db.session.close()
    return 'OK'

@socketio.on('submitGlobalWebhook')
def addChangeGlobalWebhook(message):

    if current_user.has_role('Admin'):
        webhookName = message['webhookName']
        webhookEndpoint = message['webhookEndpoint']
        webhookTrigger = int(message['webhookTrigger'])
        webhookHeader = message['webhookHeader']
        webhookPayload = message['webhookPayload']
        webhookReqType = int(message['webhookReqType'])
        webhookInputAction = message['inputAction']
        webhookInputID = message['webhookInputID']

        if webhookInputAction == 'new':
            newWebHook = webhook.globalWebhook(webhookName, webhookEndpoint, webhookHeader, webhookPayload, webhookReqType, webhookTrigger)
            db.session.add(newWebHook)
            db.session.commit()
            emit('newGlobalWebhookAck', {'webhookName': webhookName, 'requestURL':webhookEndpoint, 'requestHeader':webhookHeader, 'requestPayload':webhookPayload, 'requestType':webhookReqType, 'requestTrigger':webhookTrigger, 'requestID':newWebHook.id}, broadcast=False)
        elif webhookInputAction == 'edit':
            existingWebhookQuery = webhook.globalWebhook.query.filter_by(id=int(webhookInputID)).first()
            if existingWebhookQuery is not None:
                existingWebhookQuery.name = webhookName
                existingWebhookQuery.endpointURL = webhookEndpoint
                existingWebhookQuery.requestHeader = webhookHeader
                existingWebhookQuery.requestPayload = webhookPayload
                existingWebhookQuery.requestType = webhookReqType
                existingWebhookQuery.requestTrigger = webhookTrigger
                emit('changeGlobalWebhookAck', {'webhookName': webhookName, 'requestURL': webhookEndpoint, 'requestHeader': webhookHeader, 'requestPayload': webhookPayload, 'requestType': webhookReqType, 'requestTrigger': webhookTrigger, 'requestID': existingWebhookQuery.id}, broadcast=False)
    db.session.commit()
    db.session.close()
    return 'OK'

@socketio.on('deleteGlobalWebhook')
def deleteGlobalWebhook(message):
    webhookID = int(message['webhookID'])
    webhookQuery = webhook.globalWebhook.query.filter_by(id=webhookID).first()

    if webhookQuery is not None:
        if current_user.has_role('Admin'):
            db.session.delete(webhookQuery)
            db.session.commit()
    db.session.close()
    return 'OK'

@socketio.on('testWebhook')
def testWebhook(message):
    if current_user.is_authenticated:
        webhookID = int(message['webhookID'])
        webhookType = message['webhookType']
        channelID = None

        if 'channelID' in message:
            channelID = int(message['channelID'])

        sysSettings = cachedDbCalls.getSystemSettings()
        webhookQuery = None

        # Acquire a Channel to Test With
        channelQuery = None
        if channelID is not None:
            channelQuery = Channel.Channel.query.filter_by(id=channelID).first()
        else:
            channelQuery = Channel.Channel.query.order_by(func.rand()).first()

        # Acquire a Topic to Test With
        topic = topics.topics.query.order_by(func.rand()).first()

        # Retrieve Current Picture
        pictureLocation = current_user.pictureLocation
        if current_user.pictureLocation is None:
            pictureLocation = '/static/img/user2.png'
        else:
            pictureLocation = '/images/' + pictureLocation

        if channelQuery is not None:

            # Prepare Channel Image
            if channelQuery.imageLocation is None:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
            else:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + channelQuery.imageLocation)

            if webhookType == "global":
                if current_user.has_role("Admin"):
                    webhookQuery = webhook.globalWebhook.query.filter_by(id=webhookID).first()

            elif webhookType == "channel":
                webhookQuery = webhook.webhook.query.filter_by(id=webhookID).first()
                if webhookQuery is not None:
                    if webhookQuery.channel.id != current_user.id:
                        webhookQuery = None

            randomVideoQuery = RecordedVideo.RecordedVideo.query.order_by(func.random()).first()

            message_tasks.test_webhook.delay(webhookType, webhookQuery.id, channelname=channelQuery.channelName,
                                       channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(channelQuery.id)), channeltopic=templateFilters.get_topicName(channelQuery.topic),
                                       channelimage=channelImage, streamer=templateFilters.get_userName(channelQuery.owningUser),
                                       channeldescription=str(channelQuery.description), streamname="Testing Stream",
                                       streamurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/view/" + channelQuery.channelLoc),
                                       streamtopic=templateFilters.get_topicName(topic.id), streamimage=(sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg"),
                                       user=current_user.username, userpicture=(sysSettings.siteProtocol + sysSettings.siteAddress + str(pictureLocation)),
                                       videoname=randomVideoQuery.channelName, videodate=str(randomVideoQuery.videoDate), videodescription=randomVideoQuery.description,
                                       videotopic=templateFilters.get_topicName(randomVideoQuery.topic), videourl=(sysSettings.siteProtocol + sysSettings.siteAddress + '/play/' + str(randomVideoQuery.id)),
                                       videothumbnail=(sysSettings.siteProtocol + sysSettings.siteAddress + '/videos/' + str(randomVideoQuery.thumbnailLocation)), comment="This is just a test comment!",
                                       message="This is just a test message!")
    db.session.commit()
    db.session.close()
    return 'OK'