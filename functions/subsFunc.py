from app import app
from flask_mail import Message
import logging

from classes.shared import email
from classes import settings
from classes import subscriptions
from classes import Sec

from functions import system
from functions import cachedDbCalls
from functions.scheduled_tasks import message_tasks

from classes.shared import db

log = logging.getLogger("app.functions.subsFunc")


def processSubscriptions(channelID, subject, message, type):
    subscriptionQuery = subscriptions.channelSubs.query.filter_by(
        channelID=channelID
    ).with_entities(subscriptions.channelSubs.id, subscriptions.channelSubs.userID).all()

    sysSettings = cachedDbCalls.getSystemSettings()
    if sysSettings.maintenanceMode == False:
        if subscriptionQuery:
            system.newLog(
                2, "Sending Subscription Emails for Channel ID: " + str(channelID)
            )

            subCount = 0
            for sub in subscriptionQuery:
                send = False
                userQuery = Sec.User.query.filter_by(id=int(sub.userID)).with_entities(Sec.User.email, Sec.User.emailStream, Sec.User.emailVideo).first()
                if userQuery is not None:
                    if type == "video" and userQuery.emailVideo is True:
                        send = True
                    elif type == "stream" and userQuery.emailStream is True:
                        send = True

                    if send is True:
                        result = message_tasks.send_email.delay(
                            subject, userQuery.email, message
                        )
                        subCount = subCount + 1
            system.newLog(
                2,
                "Processed "
                + str(subCount)
                + " out of "
                + str(len(subscriptionQuery))
                + " Email Subscriptions for Channel ID: "
                + str(channelID),
            )
    db.session.commit()
    return True
