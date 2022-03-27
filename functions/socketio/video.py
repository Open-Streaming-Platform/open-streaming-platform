from flask import abort
from flask_security import current_user

from classes.shared import db, socketio
from classes import RecordedVideo
from classes import settings
from classes import notifications
from classes import subscriptions
from classes import comments
from classes import upvotes

from functions import system
from functions import webhookFunc
from functions import templateFilters
from functions import videoFunc
from functions import subsFunc
from functions import cachedDbCalls
from functions.scheduled_tasks import video_tasks, message_tasks

from app import r

@socketio.on('deleteVideo')
def deleteVideoSocketIO(message):
    if current_user.is_authenticated:
        videoID = int(message['videoID'])
        videoQuery = cachedDbCalls.getVideo(videoID)
        if videoQuery.owningUser == current_user.id:
            result = video_tasks.delete_video.delay(videoID)
            db.session.commit()
            db.session.close()
            return 'OK'
    db.session.commit()
    db.session.close()
    return abort(401)

@socketio.on('editVideo')
def editVideoSocketIO(message):
    if current_user.is_authenticated:
        videoID = int(message['videoID'])
        videoName = system.strip_html(message['videoName'])
        videoTopic = int(message['videoTopic'])
        videoDescription = message['videoDescription']
        videoAllowComments = False
        if message['videoAllowComments'] == "True" or message['videoAllowComments'] == True:
            videoAllowComments = True

        videoQuery = cachedDbCalls.getVideo(videoID)
        if videoQuery != None:
            if current_user.has_role('Admin') or videoQuery.owningUser == current_user.id:
                result = videoFunc.changeVideoMetadata(videoID, videoName, videoTopic, videoDescription, videoAllowComments)
                if result is True:
                    db.session.commit()
                    db.session.close()
                    return 'OK'
                else:
                    db.session.commit()
                    db.session.close()
                    return abort(500)
            else:
                db.session.commit()
                db.session.close()
                return abort(403)
        else:
            db.session.commit()
            db.session.close()
            return abort(500)
    else:
        db.session.commit()
        db.session.close()
        return abort(401)

@socketio.on('createClip')
def createclipSocketIO(message):
    if current_user.is_authenticated:
        videoID = int(message['videoID'])
        clipName = system.strip_html(message['clipName'])
        clipDescription = message['clipDescription']
        startTime = float(message['clipStart'])
        stopTime = float(message['clipStop'])
        videoQuery = cachedDbCalls.getVideo(videoID)
        if videoQuery.owningUser == current_user.id:
            result = video_tasks.create_video_clip.delay(videoID, startTime, stopTime, clipName, clipDescription)
            db.session.commit()
            db.session.close()
            return 'OK'
        else:
            db.session.commit()
            db.session.close()
            return abort(401)

@socketio.on('moveVideo')
def moveVideoSocketIO(message):
    if current_user.is_authenticated:
        videoID = int(message['videoID'])
        newChannel = int(message['destinationChannel'])

        result = videoFunc.moveVideo(videoID, newChannel)
        if result is True:
            db.session.commit()
            db.session.close()
            return 'OK'
        else:
            db.session.commit()
            db.session.close()
            return abort(500)
    else:
        db.session.commit()
        db.session.close()
        return abort(401)

@socketio.on('togglePublished')
def togglePublishedSocketIO(message):
    sysSettings = cachedDbCalls.getSystemSettings()
    if current_user.is_authenticated:
        videoID = int(message['videoID'])
        videoQuery = RecordedVideo.RecordedVideo.query.filter_by(owningUser=current_user.id, id=videoID).first()
        if videoQuery is not None:
            newState = not videoQuery.published
            videoQuery.published = newState

            if videoQuery.channel.imageLocation is None:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
            else:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + videoQuery.channel.imageLocation)

            if newState is True:

                message_tasks.send_webhook.delay(videoQuery.channel.id, 6, channelname=videoQuery.channel.channelName,
                           channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(videoQuery.channel.id)),
                           channeltopic=templateFilters.get_topicName(videoQuery.channel.topic),
                           channelimage=channelImage, streamer=templateFilters.get_userName(videoQuery.channel.owningUser),
                           channeldescription=str(videoQuery.channel.description), videoname=videoQuery.channelName,
                           videodate=videoQuery.videoDate, videodescription=str(videoQuery.description),
                           videotopic=templateFilters.get_topicName(videoQuery.topic),
                           videourl=(sysSettings.siteProtocol + sysSettings.siteAddress + '/play/' + str(videoQuery.id)),
                           videothumbnail=(sysSettings.siteProtocol + sysSettings.siteAddress + '/videos/' + str(videoQuery.thumbnailLocation)))

                subscriptionQuery = subscriptions.channelSubs.query.filter_by(channelID=videoQuery.channel.id).all()
                for sub in subscriptionQuery:
                    # Create Notification for Channel Subs
                    newNotification = notifications.userNotification(templateFilters.get_userName(videoQuery.channel.owningUser) + " has posted a new video to " + videoQuery.channel.channelName + " titled " + videoQuery.channelName, '/play/' + str(videoQuery.id), "/images/" + str(videoQuery.channel.owner.pictureLocation), sub.userID)
                    db.session.add(newNotification)
                db.session.commit()

                subsFunc.processSubscriptions(videoQuery.channel.id, sysSettings.siteName + " - " + videoQuery.channel.channelName + " has posted a new video", "<html><body><img src='" +
                                     sysSettings.siteProtocol + sysSettings.siteAddress + sysSettings.systemLogo + "'><p>Channel " + videoQuery.channel.channelName + " has posted a new video titled <u>" +
                                     videoQuery.channelName + "</u> to the channel.</p><p>Click this link to watch<br><a href='" + sysSettings.siteProtocol + sysSettings.siteAddress + "/play/" +
                                     str(videoQuery.id) + "'>" + videoQuery.channelName + "</a></p>", "video")

            db.session.commit()
            db.session.close()
            return 'OK'
        else:
            db.session.commit()
            db.session.close()
            return abort(500)
    else:
        db.session.commit()
        db.session.close()
        return abort(401)

@socketio.on('togglePublishedClip')
def togglePublishedClipSocketIO(message):
    if current_user.is_authenticated:
        clipID = int(message['clipID'])
        clipQuery = RecordedVideo.Clips.query.filter_by(id=clipID).first()

        if clipQuery is not None and current_user.id == clipQuery.recordedVideo.owningUser:
            newState = not clipQuery.published
            clipQuery.published = newState

            if newState is True:

                subscriptionQuery = subscriptions.channelSubs.query.filter_by(channelID=clipQuery.recordedVideo.channel.id).all()
                for sub in subscriptionQuery:
                    # Create Notification for Channel Subs
                    newNotification = notifications.userNotification(templateFilters.get_userName(clipQuery.recordedVideo.owningUser) + " has posted a new clip to " +
                                                                     clipQuery.recordedVideo.channel.channelName + " titled " + clipQuery.clipName,'/clip/' +
                                                                     str(clipQuery.id),"/images/" + str(clipQuery.recordedVideo.channel.owner.pictureLocation), sub.userID)
                    db.session.add(newNotification)
            db.session.commit()
            db.session.close()
            return 'OK'
        else:
            db.session.commit()
            db.session.close()
            return abort(500)
    else:
        db.session.commit()
        db.session.close()
        return abort(401)

@socketio.on('editClip')
def changeClipMetadataSocketIO(message):
    if current_user.is_authenticated:
        clipID = int(message['clipID'])
        clipName = message['clipName']
        clipDescription = message['clipDescription']

        result = videoFunc.changeClipMetadata(clipID, clipName, clipDescription)

        if result is True:
            db.session.commit()
            db.session.close()
            return 'OK'
        else:
            db.session.commit()
            db.session.close()
            return abort(500)
    else:
        db.session.commit()
        db.session.close()
        return abort(401)

@socketio.on('deleteClip')
def deleteClipSocketIO(message):
    if current_user.is_authenticated:
        clipID = int(message['clipID'])
        clipQuery = RecordedVideo.Clips.query.filter_by(id=clipID).first()
        if clipQuery.recordedVideo.owningUser == current_user.id:
            result = video_tasks.delete_video_clip.delay(clipID)
            db.session.commit()
            db.session.close()
            return 'OK'
        else:
            db.session.commit()
            db.session.close()
            return abort(401)
    else:
        db.session.commit()
        db.session.close()
        return abort(401)

@socketio.on('commentID')
def deleteVideoCommentSocketIO(message):
    commentID = int(message['commentID'])
    commentQuery = comments.videoComments.query.filter_by(id=commentID).first()
    if commentQuery is not None:
        recordedVid = RecordedVideo.RecordedVideo.query.filter_by(commentQuery.videoID).with_entities(RecordedVideo.RecordedVideo.id, RecordedVideo.RecordedVideo.owningUser).first()
        if current_user.has_role('Admin') or recordedVid.owningUser == current_user.id or commentQuery.userID == current_user.id:
            upvoteQuery = upvotes.commentUpvotes.query.filter_by(commentID=commentQuery.id).all()
            for vote in upvoteQuery:
                db.session.delete(vote)
            db.session.delete(commentQuery)
            db.session.commit()
            system.newLog(4, "Video Comment Deleted by " + current_user.username + "to Video ID #" + str(recordedVid.id))
    db.session.commit()
    db.session.close()
    return 'OK'
