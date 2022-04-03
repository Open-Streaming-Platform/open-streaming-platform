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
    roleIDQuery = Sec.Role.query.filter_by(name='Admin').first()
    query_user_role = Sec.roles_users.query(Sec.roles_users.role_id == roleIDQuery.id).all()
    notificationArray = []
    for entry in query_user_role:
        notificationID = sendNotification(message, entry.user_id)
        notificationArray.append(notificationID)
    return notificationArray