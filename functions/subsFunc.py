from app import app
from flask_mail import Message

from classes.shared import email
from classes import settings
from classes import subscriptions
from classes import Sec

from functions import system

@system.asynch
def runSubscription(subject, destination, message):
    with app.app_context():
        sysSettings = settings.settings.query.first()
        finalMessage = message + "<p>If you would like to unsubscribe, click the link below: <br><a href='" + sysSettings.siteProtocol + sysSettings.siteAddress + "/unsubscribe?email=" + destination + "'>Unsubscribe</a></p></body></html>"
        msg = Message(subject=subject, recipients=[destination])
        msg.sender = sysSettings.siteName + "<" + sysSettings.smtpSendAs + ">"
        msg.body = finalMessage
        msg.html = finalMessage
        email.send(msg)
        return True

def processSubscriptions(channelID, subject, message):
    subscriptionQuery = subscriptions.channelSubs.query.filter_by(channelID=channelID).all()
    if subscriptionQuery:
        system.newLog(2, "Sending Subscription Emails for Channel ID: " + str(channelID))

        subCount = 0
        for sub in subscriptionQuery:
            userQuery = Sec.User.query.filter_by(id=int(sub.userID)).first()
            if userQuery is not None:
                result = runSubscription(subject, userQuery.email, message)
                subCount = subCount + 1
        system.newLog(2, "Processed " + str(subCount) + " out of " + str(len(subscriptionQuery)) + " Email Subscriptions for Channel ID: " + str(channelID) )
    return True