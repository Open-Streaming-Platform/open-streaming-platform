from app import app
from flask_mail import Message
import logging

from classes.shared import email
from classes import settings
from classes import subscriptions
from classes import Sec

from functions import system
from functions import cachedDbCalls
from classes.shared import db

log = logging.getLogger('app.functions.subsFunc')

@system.asynch
def runSubscription(subject, destination, message):
    with app.app_context():
        sysSettings = cachedDbCalls.getSystemSettings()
        finalMessage = message + "<p>If you would like to unsubscribe, click the link below: <br><a href='" + sysSettings.siteProtocol + sysSettings.siteAddress + "/unsubscribe?email=" + destination + "'>Unsubscribe</a></p></body></html>"
        msg = Message(subject=subject, recipients=[destination])
        msg.sender = sysSettings.siteName + "<" + sysSettings.smtpSendAs + ">"
        msg.body = finalMessage
        msg.html = finalMessage
        email.send(msg)
        return True

def processSubscriptions(channelID, subject, message):
    subscriptionQuery = subscriptions.channelSubs.query.filter_by(channelID=channelID).all()

    sysSettings = cachedDbCalls.getSystemSettings()
    if sysSettings.maintenanceMode == False:
        if subscriptionQuery:
            system.newLog(2, "Sending Subscription Emails for Channel ID: " + str(channelID))

            subCount = 0
            for sub in subscriptionQuery:
                userQuery = Sec.User.query.filter_by(id=int(sub.userID)).first()
                if userQuery is not None:
                    result = runSubscription(subject, userQuery.email, message)
                    subCount = subCount + 1
            system.newLog(2, "Processed " + str(subCount) + " out of " + str(len(subscriptionQuery)) + " Email Subscriptions for Channel ID: " + str(channelID) )
    db.session.commit()
    return True