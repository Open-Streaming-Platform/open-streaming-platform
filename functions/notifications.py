from classes.shared import db
from classes import notifications, Sec

def sendMessage(subject, message, fromUser, toUser):
    newMessage = notifications.userMessage(subject, message, fromUser, toUser)
    db.session.add(newMessage)
    db.session.commit()
    return newMessage.messageID

def sendNotification(message, toUserID):
    newNotification = notifications.userNotification(message, toUserID)
    db.session.add(newNotification)
    db.session.commit()
    return newNotification.notificationID

def sendAdminNotification(message):
    adminList = []
    userQuery = Sec.User.query.all()
    for user in userQuery:
        if user.has_role('Admin'):
            adminList.append(user)
    notificationArray = []
    for entry in adminList:
        notificationID = sendNotification(message, entry.id)
        notificationArray.append(notificationID)
    db.session.commit()
    db.session.close()
    return notificationArray