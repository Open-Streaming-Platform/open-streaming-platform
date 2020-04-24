from flask_security import current_user
from flask_socketio import emit

from classes.shared import db, socketio
from classes import Channel
from classes import webhook

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