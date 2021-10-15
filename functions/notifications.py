from classes.shared import db
from classes import notifications, Sec

def sendMessage(subject, message, fromUser, toUser):
    newMessage = notifications.userMessage(subject, message, fromUser, toUser)
    db.session.add(newMessage)
    db.session.commit()
    return newMessage.messageID