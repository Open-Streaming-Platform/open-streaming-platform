from flask_security import current_user
from flask_socketio import emit

from classes.shared import db, socketio
from classes import notifications

from functions.scheduled_tasks import message_tasks
from functions import cachedDbCalls

@socketio.on('sendMessage')
def sendMessage(message):
    if current_user.is_authenticated:
        sendMessageTo = message['sendMessageTo']
        messageSubject = message['messageSubject']
        messageContent = message['messageContent']
        for destination in sendMessageTo:
            UserCheck = cachedDbCalls.getUser(int(destination['value']))
            if UserCheck is not None:
                message_tasks.send_message.delay(messageSubject, messageContent, current_user.id, UserCheck.id)
    return 'OK'

@socketio.on('getMessage')
def getMessage(message):
    if current_user.is_authenticated:
        messageID = message['messageID']
        messageQuery = notifications.userMessage.query.filter_by(id=messageID, toUserID=current_user.id).first()
        if messageQuery != None:
            fromUserQuery = cachedDbCalls.getUser(messageQuery.fromUserID)
            emit('returnMessage', {'status': 'success', 'fromUser': messageQuery.fromUserID, 'fromUsername': fromUserQuery.username, 'fromUserPhoto': fromUserQuery.pictureLocation, 'subject': messageQuery.subject,
                                   'timestamp': str(messageQuery.timestamp), 'content': messageQuery.message, 'id': messageQuery.id}, broadcast=False)
            messageQuery.read = True
        db.session.commit()
        db.session.close()
    return 'OK'

@socketio.on('deleteMessage')
def deleteMessage(message):
    if current_user.is_authenticated:
        if 'messageId' in message:
            messages = message['messageId']
            for message in messages:
                messageQuery = notifications.userMessage.query.filter_by(id=int(message), toUserID=current_user.id).first()
                if messageQuery is not None:
                    db.session.delete(messageQuery)
                    db.session.commit()
            db.session.close()
    return 'OK'