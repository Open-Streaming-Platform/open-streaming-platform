from flask_socketio import emit
from flask_security import current_user

from classes.shared import db, socketio, limiter
from classes import Channel
from classes import settings
from classes import notifications
from classes import subscriptions

from functions import webhookFunc
from functions import templateFilters
from functions import cachedDbCalls

from functions.scheduled_tasks import message_tasks

@socketio.on('toggleChannelSubscription')
@limiter.limit("10/minute")
def toggle_chanSub(payload):
    if current_user.is_authenticated:
        sysSettings = cachedDbCalls.getSystemSettings()
        if 'channelID' in payload:
            #channelQuery = Channel.Channel.query.filter_by(id=int(payload['channelID'])).first()
            channelQuery = cachedDbCalls.getChannel(int(payload['channelID']))
            if channelQuery is not None:
                currentSubscription = subscriptions.channelSubs.query.filter_by(channelID=channelQuery.id, userID=current_user.id).first()
                subState = False
                if currentSubscription is None:
                    newSub = subscriptions.channelSubs(channelQuery.id, current_user.id)
                    db.session.add(newSub)
                    subState = True

                    channelImage = None
                    if channelQuery.imageLocation is None:
                        channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
                    else:
                        channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + channelQuery.imageLocation)

                    pictureLocation = current_user.pictureLocation
                    if current_user.pictureLocation is None:
                        pictureLocation = '/static/img/user2.png'
                    else:
                        pictureLocation = '/images/' + pictureLocation

                    # Create Notification for Channel Owner on New Subs
                    newNotification = notifications.userNotification(current_user.username + " has subscribed to " + channelQuery.channelName, "/channel/" + str(channelQuery.id), "/images/" + str(current_user.pictureLocation), channelQuery.owningUser)
                    db.session.add(newNotification)
                    db.session.commit()

                    message_tasks.send_webhook.delay(channelQuery.id, 10, channelname=channelQuery.channelName,
                               channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(channelQuery.id)),
                               channeltopic=templateFilters.get_topicName(channelQuery.topic),
                               channelimage=str(channelImage), streamer=templateFilters.get_userName(channelQuery.owningUser),
                               channeldescription=str(channelQuery.description),
                               user=current_user.username, userpicture=sysSettings.siteProtocol + sysSettings.siteAddress + str(pictureLocation))
                else:
                    db.session.delete(currentSubscription)
                db.session.commit()
                db.session.close()
                emit('sendChanSubResults', {'state': subState}, broadcast=False)
    db.session.close()
    return 'OK'

@socketio.on('markNotificationAsRead')
def markUserNotificationRead(message):
    notificationID = message['data']
    notificationQuery = notifications.userNotification.query.filter_by(notificationID=notificationID, userID=current_user.id).first()
    if notificationQuery is not None:
        notificationQuery.read = True
    db.session.commit()
    db.session.close()
    return 'OK'