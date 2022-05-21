from classes.shared import db
from classes import notifications, Sec

def sendMessage(subject, message, fromUser, toUser):
    newMessage = notifications.userMessage(subject, message, fromUser, toUser)
    db.session.add(newMessage)
    db.session.commit()
    return newMessage.messageID

def sendNotification(message, link, image, toUserID):
    newNotification = notifications.userNotification(message, link, image, toUserID)
    db.session.add(newNotification)
    db.session.commit()
    return newNotification.notificationID

def sendAdminNotification(message, link, image):
    adminList = []
    userQuery = Sec.User.query.all()
    for user in userQuery:
        if user.has_role('Admin'):
            adminList.append(user)
    notificationArray = []
    for admin in adminList:
        notificationID = sendNotification(message, link, image, admin.id)
        notificationArray.append(notificationID)
    db.session.commit()
    return notificationArray