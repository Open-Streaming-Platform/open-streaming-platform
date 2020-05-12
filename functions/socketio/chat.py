from flask import request
from flask_security import current_user
from flask_socketio import emit

from classes.shared import db, socketio, limiter
from classes import settings
from classes import Channel
from classes import Sec
from classes import banList

from functions import webhookFunc
from functions import templateFilters
from functions import system

from app import r

@socketio.on('text')
@limiter.limit("1/second")
def text(message):
    """Sent by a client when the user entered a new message.
    The message is sent to all people in the room."""
    room = message['room']
    msg = system.strip_html(message['msg'])

    sysSettings = settings.settings.query.first()

    channelQuery = Channel.Channel.query.filter_by(channelLoc=room).first()

    if channelQuery is not None:

        userSID = request.cookies.get('ospSession')
        if userSID.encode('utf-8') not in r.smembers(channelQuery.channelLoc + '-streamSIDList'):
            r.sadd(channelQuery.channelLoc + '-streamSIDList', userSID)
        if current_user.username.encode('utf-8') not in r.lrange(channelQuery.channelLoc + '-streamUserList', 0, -1):
            r.rpush(channelQuery.channelLoc + '-streamUserList', current_user.username)

        pictureLocation = current_user.pictureLocation
        if current_user.pictureLocation is None:
            pictureLocation = '/static/img/user2.png'
        else:
            pictureLocation = '/images/' + pictureLocation

        if msg.startswith('/'):
            if msg.startswith('/test '):
                commandArray = msg.split(' ',1)
                if len(commandArray) >= 2:
                    command = commandArray[0]
                    target = commandArray[1]
                    msg = 'Test Received - Success: ' + command + ":" + target
            elif msg == ('/sidlist'):
                if current_user.has_role('Admin'):
                    msg = str((r.smembers(channelQuery.channelLoc + '-streamSIDList')))
            elif msg.startswith('/mute'):
                if (current_user.has_role('Admin')) or (current_user.id == channelQuery.owningUser):
                    channelQuery.channelMuted = True
                    db.session.commit()
                    msg = "<b> *** " + current_user.username + " has muted the chat channel ***"
                    emit('message', {'user': current_user.username, 'image': pictureLocation, 'msg': msg}, room=room)
                    db.session.commit()
                    db.session.close()
                    return
            elif msg.startswith('/unmute'):
                if (current_user.has_role('Admin')) or (current_user.id == channelQuery.owningUser):
                    channelQuery.channelMuted = False
                    db.session.commit()
                    msg = "<b> *** " + current_user.username + " has unmuted the chat channel ***"
                    emit('message', {'user': current_user.username, 'image': pictureLocation, 'msg': msg}, room=room)
                    db.session.commit()
                    db.session.close()
                    return
            elif msg.startswith('/ban '):
                if (current_user.has_role('Admin')) or (current_user.id == channelQuery.owningUser):
                    commandArray = msg.split(' ', 1)
                    if len(commandArray) >= 2:
                        command = commandArray[0]
                        target = commandArray[1]

                        userQuery = Sec.User.query.filter_by(username=target).first()

                        if userQuery is not None:
                            newBan = banList.banList(room, userQuery.id)
                            db.session.add(newBan)
                            db.session.commit()
                            msg = '<b>*** ' + target + ' has been banned ***</b>'
            elif msg.startswith('/unban '):
                if (current_user.has_role('Admin')) or (current_user.id == channelQuery.owningUser):
                    commandArray = msg.split(' ', 1)
                    if len(commandArray) >= 2:
                        command = commandArray[0]
                        target = commandArray[1]

                        userQuery = Sec.User.query.filter_by(username=target).first()

                        if userQuery is not None:
                            banQuery = banList.banList.query.filter_by(userID=userQuery.id, channelLoc=room).first()
                            if banQuery is not None:
                                db.session.delete(banQuery)
                                db.session.commit()

                                msg = '<b>*** ' + target + ' has been unbanned ***</b>'

        banQuery = banList.banList.query.filter_by(userID=current_user.id, channelLoc=room).first()

        if banQuery is None:
            if channelQuery.channelMuted == False or channelQuery.owningUser == current_user.id:
                flags = ""
                if current_user.id == channelQuery.owningUser:
                    flags = "Owner"

                if channelQuery.imageLocation is None:
                    channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
                else:
                    channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + channelQuery.imageLocation)

                streamName = None
                streamTopic = None

                if channelQuery.stream:
                    streamName = channelQuery.stream[0].streamName
                    streamTopic = channelQuery.stream[0].topic
                else:
                    streamName = channelQuery.channelName
                    streamTopic = channelQuery.topic

                webhookFunc.runWebhook(channelQuery.id, 5, channelname=channelQuery.channelName,
                           channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(channelQuery.id)),
                           channeltopic=templateFilters.get_topicName(channelQuery.topic),
                           channelimage=channelImage, streamer=templateFilters.get_userName(channelQuery.owningUser),
                           channeldescription=str(channelQuery.description),
                           streamname=streamName,
                           streamurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/view/" + channelQuery.channelLoc),
                           streamtopic=templateFilters.get_topicName(streamTopic), streamimage=(sysSettings.siteProtocol + sysSettings.siteAddress + "/stream-thumb/" + channelQuery.channelLoc + ".png"),
                           user=current_user.username, userpicture=sysSettings.siteProtocol + sysSettings.siteAddress + pictureLocation, message=msg)
                emit('message', {'user': current_user.username, 'image': pictureLocation, 'msg':msg, 'flags':flags}, room=room)
                db.session.commit()
                db.session.close()

            else:
                msg = '<b>*** Chat Channel has been muted and you can not send messages ***</b>'
                emit('message', {'user': current_user.username, 'image': pictureLocation, 'msg': msg}, broadcast=False)
                db.session.commit()
                db.session.close()

        elif banQuery:
            msg = '<b>*** You have been banned and can not send messages ***</b>'
            emit('message', {'user': current_user.username, 'image': pictureLocation, 'msg': msg}, broadcast=False)
            db.session.commit()
            db.session.close()
    db.session.commit()
    db.session.close()
    return 'OK'