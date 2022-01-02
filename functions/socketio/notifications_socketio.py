from flask_security import current_user

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