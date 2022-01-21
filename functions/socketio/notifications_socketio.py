from flask_security import current_user
from flask_socketio import emit
import markdown as md

from classes.shared import db, socketio
from classes import notifications, banList

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
                existingBanSearch = banList.messageBanList.query.filter_by(userID=UserCheck.id, messageFrom=current_user.id).first()
                if existingBanSearch is None:
                    message_tasks.send_message.delay(messageSubject, messageContent, current_user.id, UserCheck.id)
                else:
                    emit('messageBanWarning', {'message':'User ' + UserCheck.username + ' has blocked messages from your account. Message Not Sent!'}, broadcast=False)
    return 'OK'

@socketio.on('getMessage')
def getMessage(message):
    if current_user.is_authenticated:
        messageID = message['messageID']
        messageQuery = notifications.userMessage.query.filter_by(id=messageID, toUserID=current_user.id).first()
        if messageQuery != None:
            fromUserQuery = cachedDbCalls.getUser(messageQuery.fromUserID)
            emit('returnMessage', {'status': 'success', 'fromUser': messageQuery.fromUserID, 'fromUsername': fromUserQuery.username, 'fromUserPhoto': fromUserQuery.pictureLocation, 'subject': messageQuery.subject,
                                   'timestamp': str(messageQuery.timestamp), 'content': md.markdown(messageQuery.message), 'id': messageQuery.id}, broadcast=False)
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

@socketio.on('markMessageRead')
def markMessagesRead(message):
    if current_user.is_authenticated:
        if 'messageId' in message:
            messages = message['messageId']
            for message in messages:
                messageQuery = notifications.userMessage.query.filter_by(id=int(message), toUserID=current_user.id).first()
                if messageQuery is not None:
                    messageQuery.read = True
                    db.session.commit()
            db.session.close()
    return 'OK'

@socketio.on('addToMessageBanList')
def addToBanList(message):
    if current_user.is_authenticated:
        if 'banListUsers' in message:
            requestedBanList = message['banListUsers']
            for user in requestedBanList:
                UserCheck = cachedDbCalls.getUser(int(user['value']))
                if UserCheck is not None and current_user.id != int(user['value']):
                    existingBanSearch = banList.messageBanList.query.filter_by(userID=current_user.id, messageFrom=UserCheck.id).first()
                    if existingBanSearch is None:
                        newBan = banList.messageBanList(current_user.id, UserCheck.id)
                        db.session.add(newBan)
                    db.session.commit()
            db.session.close()
    return 'OK'

@socketio.on('removeFromMessageBanList')
def removeFromBanList(message):
    if current_user.is_authenticated:
        if 'userID' in message:
            userID = message['userID']
            existingBanSearch = banList.messageBanList.query.filter_by(userID=current_user.id, messageFrom=int(userID)).first()
            if existingBanSearch is not None:
                db.session.delete(existingBanSearch)
            db.session.commit()
        db.session.close()
    return 'OK'