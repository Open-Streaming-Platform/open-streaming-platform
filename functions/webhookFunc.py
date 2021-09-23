import json
import requests
import logging

from classes.shared import db
from classes import webhook

from functions import system

log = logging.getLogger('app.functions.database')

@system.asynch
def runWebhook(channelID, triggerType, **kwargs):
    webhookQueue = []
    if channelID != "ZZZ":

        webhookQuery = webhook.webhook.query.filter_by(channelID=channelID, requestTrigger=triggerType).all()
        webhookQueue.append(webhookQuery)

    globalWebhookQuery = webhook.globalWebhook.query.filter_by(requestTrigger=triggerType).all()
    webhookQueue.append(globalWebhookQuery)

    for queue in webhookQueue:
        if queue:
            for hook in queue:
                url = hook.endpointURL
                payload = processWebhookVariables(hook.requestPayload, **kwargs)
                header = json.loads(hook.requestHeader)
                requestType = hook.requestType
                try:
                    if requestType == 0:
                        r = requests.post(url, headers=header, data=payload)
                    elif requestType == 1:
                        r = requests.get(url, headers=header, data=payload)
                    elif requestType == 2:
                        r = requests.put(url, headers=header, data=payload)
                    elif requestType == 3:
                        r = requests.delete(url, headers=header, data=payload)
                except:
                    pass
                system.newLog(8, "Processing Webhook for ID #" + str(hook.id) + " - Destination:" + str(url))
    db.session.commit()
    db.session.close()
    return True

@system.asynch
def testWebhook(webhookType, webhookID, **kwargs):
    system.newLog(8, "Testing Webhook for ID #" + str(webhookID) +", Type: " + webhookType)
    webhookQuery = None
    if webhookType == "channel":
        webhookQuery = webhook.webhook.query.filter_by(id=webhookID).first()
    elif webhookType == "global":
        webhookQuery = webhook.globalWebhook.query.filter_by(id=webhookID).first()
    if webhookQuery is not None:
        url = webhookQuery.endpointURL
        payload = processWebhookVariables(webhookQuery.requestPayload, **kwargs)
        header = json.loads(webhookQuery.requestHeader)
        requestType = webhookQuery.requestType
        try:
            if requestType == 0:
                r = requests.post(url, headers=header, data=payload)
            elif requestType == 1:
                r = requests.get(url, headers=header, data=payload)
            elif requestType == 2:
                r = requests.put(url, headers=header, data=payload)
            elif requestType == 3:
                r = requests.delete(url, headers=header, data=payload)
        except Exception as e:
            print("Webhook Error-" + str(e) )
        system.newLog(8, "Completed Webhook Test for ID #" + str(webhookQuery.id) + " - Destination:" + str(url))

def processWebhookVariables(payload, **kwargs):
    for key, value in kwargs.items():
        replacementValue = ("%" + key + "%")
        payload = payload.replace(replacementValue, str(value))
    return payload