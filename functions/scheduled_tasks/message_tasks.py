from celery.canvas import subtask
from celery.result import AsyncResult

import logging, json, requests
from classes.shared import celery, db
from classes import notifications, Sec, webhook

from functions import notifications, webhookFunc, system

log = logging.getLogger('app.functions.scheduler.message_tasks')

def setup_message_tasks(sender, **kwargs):
    pass

@celery.task(bind=True)
def send_message(self, subject, message, fromUser, toUser):
    result = notifications.sendMessage(subject, message, fromUser, toUser)
    log.info({"level": "info", "taskID": self.request.id.__str__(), "message": "Message Sent", "subject": subject, "from": fromUser, "to": toUser})
    return True

@celery.task(bind=True)
def send_mass_message(self, subject, message, fromUser):
    for user in Sec.User.query.all():
        results = subtask('functions.scheduled_tasks.message_tasks.send_message', args=(subject, message, fromUser, user.id )).apply_async()
    log.info({"level": "info", "taskID": self.request.id.__str__(), "message": "Mass Message Sent", "subject": subject, "from": fromUser})
    return True

@celery.task(bind=True)
def send_webhook(self, channelID, triggerType, **kwargs):
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
                payload = webhookFunc.processWebhookVariables(hook.requestPayload, **kwargs)
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

@celery.task(bind=True)
def test_webhook(self, webhookType, webhookID, **kwargs):
    system.newLog(8, "Testing Webhook for ID #" + str(webhookID) +", Type: " + webhookType)
    webhookQuery = None
    if webhookType == "channel":
        webhookQuery = webhook.webhook.query.filter_by(id=webhookID).first()
    elif webhookType == "global":
        webhookQuery = webhook.globalWebhook.query.filter_by(id=webhookID).first()
    if webhookQuery is not None:
        url = webhookQuery.endpointURL
        payload = webhookFunc.processWebhookVariables(webhookQuery.requestPayload, **kwargs)
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