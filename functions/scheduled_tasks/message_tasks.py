import datetime

from celery.canvas import subtask
from celery.result import AsyncResult
from flask_mail import Message

import logging, json, requests
from classes.shared import celery, db, email
from classes import notifications, Sec, webhook

from app import config

from functions import notifications, webhookFunc, system, cachedDbCalls, templateFilters

log = logging.getLogger('app.functions.scheduler.message_tasks')

def setup_message_tasks(sender, **kwargs):
    pass

@celery.task(bind=True)
def send_email(self, subject, destination, message):
    sysSettings = cachedDbCalls.getSystemSettings()
    finalMessage = message + "<p>If you would like to unsubscribe, click the link below: <br><a href='" + sysSettings.siteProtocol + sysSettings.siteAddress + "/unsubscribe?email=" + destination + "'>Unsubscribe</a></p></body></html>"
    msg = Message(subject=subject, recipients=[destination])
    msg.sender = sysSettings.siteName + "<" + config.smtpSendAs + ">"
    msg.body = finalMessage
    msg.html = finalMessage
    email.send(msg)
    log.info({"level": "info", "taskID": self.request.id.__str__(), "message": "Email Sent", "subject": subject, "to": destination})
    return True

@celery.task(bind=True)
def send_message(self, subject, message, fromUser, toUser):
    sysSettings = cachedDbCalls.getSystemSettings()
    result = notifications.sendMessage(subject, message, fromUser, toUser)
    userNotificationQuery = Sec.User.query.filter_by(id=toUser).with_entities(Sec.User.email, Sec.User.emailMessage).first()
    if userNotificationQuery is not None:
        if userNotificationQuery.emailMessage is True:
            shortMessage = (message[:75] + '..') if len(message) > 75 else message
            fullSiteURL = sysSettings.siteProtocol + sysSettings.siteAddress + '/messages'
            emailContent = """
            <div>
                A user has sent a message to an account associated with you.<br>
                <ul>
                  <li><b>From: </b>""" + templateFilters.get_userName(fromUser) + """</li>
                  <li><b>Time Sent: </b>""" + str(datetime.datetime.now()) + """</li>
                  <li><b>Message: </b>""" + shortMessage + """</li>
                </ul>
                To view the full message, visit <a href='""" + fullSiteURL + """'>""" + fullSiteURL + """</a>
            </div>
            """
            send_email.delay(sysSettings.siteName + ' - New Message Notification', userNotificationQuery.email, emailContent)
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
    return True