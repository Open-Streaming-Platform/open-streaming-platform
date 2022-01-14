import os
import time
import hashlib
import datetime
import logging

from flask import Blueprint, request, redirect, current_app, abort

from classes.shared import db, celery
from classes import Sec
from classes import RecordedVideo
from classes import subscriptions
from classes import notifications
from classes import Channel
from classes import Stream
from classes import settings
from classes import upvotes
from classes import logs
from classes import topics

from functions import webhookFunc
from functions import system
from functions import templateFilters
from functions import subsFunc
from functions import videoFunc
from functions import xmpp
from functions import cachedDbCalls
from functions.scheduled_tasks import message_tasks

log = logging.getLogger('app.functions.rtmpFunctions')

def rtmp_stage1_streamkey_check(key, ipaddress):
    sysSettings = cachedDbCalls.getSystemSettings()

    channelRequest = Channel.Channel.query.filter_by(streamKey=key).first()

    currentTime = datetime.datetime.utcnow()

    if channelRequest is not None:
        userQuery = Sec.User.query.filter_by(id=channelRequest.owningUser).first()
        if userQuery is not None:
            if userQuery.has_role('Streamer'):

                if not userQuery.active:
                    returnMessage = {'time': str(currentTime), 'request': 'Stage1', 'success': False, 'channelLoc': channelRequest.channelLoc, 'type': None, 'ipAddress': str(ipaddress), 'message': 'Unauthorized User - User has been disabled'}
                    return returnMessage

                # Checks for is there are any existing live streams and terminates them
                existingStreamQuery = Stream.Stream.query.filter_by(active=True, linkedChannel=channelRequest.id).all()
                if existingStreamQuery:
                    for stream in existingStreamQuery:
                        db.session.delete(stream)
                    db.session.commit()

                # Checks for is there are any pending live streams and terminates them
                existingStreamQuery = Stream.Stream.query.filter_by(pending=True, linkedChannel=channelRequest.id).all()
                if existingStreamQuery:
                    for stream in existingStreamQuery:
                        db.session.delete(stream)
                    db.session.commit()

                defaultStreamName = templateFilters.normalize_date(str(currentTime))
                if channelRequest.defaultStreamName != "":
                    defaultStreamName = channelRequest.defaultStreamName

                newStream = Stream.Stream(key, defaultStreamName, int(channelRequest.id), channelRequest.topic)
                db.session.add(newStream)
                db.session.commit()

                if sysSettings.adaptiveStreaming:
                    returnMessage = {'time': str(currentTime), 'request': 'Stage1', 'success': True, 'channelLoc': channelRequest.channelLoc, 'type': 'adaptive', 'ipAddress': str(ipaddress), 'message': 'Success - Passing to Stage 2 - Adaptive'}
                    return returnMessage
                else:
                    returnMessage = {'time': str(currentTime), 'request': 'Stage1', 'success': True, 'channelLoc': channelRequest.channelLoc, 'type': 'standard', 'ipAddress': str(ipaddress), 'message': 'Success - Passing to Stage 2 - Standard'}
                    return returnMessage

            else:
                returnMessage = {'time': str(currentTime), 'request': 'Stage1', 'success': False, 'channelLoc': channelRequest.channelLoc, 'type': None, 'ipAddress': str(ipaddress), 'message': 'Unauthorized User - Missing Streamer Role'}
                db.session.close()
                return returnMessage
        else:
            returnMessage = {'time': str(currentTime), 'request': 'Stage1', 'success': False, 'channelLoc': channelRequest.channelLoc, 'type': None, 'ipAddress': str(ipaddress), 'message': 'Unauthorized User - No Such User'}
            db.session.close()
            return returnMessage
    else:
        returnedResult = {'time': str(currentTime), 'request': 'Stage1', 'success': False, 'channelLoc': None, 'type': None, 'ipAddress': str(ipaddress), 'message': 'Unauthorized Key'}
        log.warning(returnedResult)
        returnMessage = returnedResult
        db.session.close()
        return returnMessage

def rtmp_stage2_user_auth_check(channelLoc, ipaddress, authorizedRTMP):
    sysSettings = cachedDbCalls.getSystemSettings()

    currentTime = datetime.datetime.utcnow()

    requestedChannel = Channel.Channel.query.filter_by(channelLoc=channelLoc).first()

    if requestedChannel is not None:
        authedStream = Stream.Stream.query.filter_by(pending=True, streamKey=requestedChannel.streamKey).first()

        if authedStream is not None:
            if authorizedRTMP is not None:
                authedStream.rtmpServer = authorizedRTMP

            authedStream.currentViewers = int(xmpp.getChannelCounts(requestedChannel.channelLoc))
            authedStream.totalViewers = int(xmpp.getChannelCounts(requestedChannel.channelLoc))
            authedStream.active = True
            authedStream.pending = False
            db.session.commit()

            if requestedChannel.imageLocation is None:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
            else:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + requestedChannel.imageLocation)

            message_tasks.send_webhook.delay(requestedChannel.id, 0, channelname=requestedChannel.channelName, channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(requestedChannel.id)), channeltopic=requestedChannel.topic,
                       channelimage=channelImage, streamer=templateFilters.get_userName(requestedChannel.owningUser), channeldescription=str(requestedChannel.description),
                       streamname=authedStream.streamName, streamurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/view/" + requestedChannel.channelLoc), streamtopic=templateFilters.get_topicName(authedStream.topic),
                       streamimage=(sysSettings.siteProtocol + sysSettings.siteAddress + "/stream-thumb/" + requestedChannel.channelLoc + ".png"))

            subscriptionQuery = subscriptions.channelSubs.query.filter_by(channelID=requestedChannel.id).all()
            for sub in subscriptionQuery:
                # Create Notification for Channel Subs
                newNotification = notifications.userNotification(templateFilters.get_userName(requestedChannel.owningUser) + " has started a live stream in " + requestedChannel.channelName, "/view/" + str(requestedChannel.channelLoc),
                                                                 "/images/" + str(requestedChannel.owner.pictureLocation), sub.userID)
                db.session.add(newNotification)
            db.session.commit()

            try:
                subsFunc.processSubscriptions(requestedChannel.id,
                                 sysSettings.siteName + " - " + requestedChannel.channelName + " has started a stream",
                                 "<html><body><img src='" + sysSettings.siteProtocol + sysSettings.siteAddress + sysSettings.systemLogo + "'><p>Channel " + requestedChannel.channelName +
                                 " has started a new video stream.</p><p>Click this link to watch<br><a href='" + sysSettings.siteProtocol + sysSettings.siteAddress + "/view/" + str(requestedChannel.channelLoc)
                                 + "'>" + requestedChannel.channelName + "</a></p>")
            except:
                system.newLog(0, "Subscriptions Failed due to possible misconfiguration")

            returnMessage = {'time': str(currentTime), 'request': 'Stage2', 'success': True, 'channelLoc': requestedChannel.channelLoc, 'ipAddress': str(ipaddress), 'adaptive': sysSettings.adaptiveStreaming, 'message': 'Success - Stream Authenticated & Initialized'}
            db.session.close()
            return returnMessage
        else:
            returnMessage = {'time': str(currentTime), 'request': 'Stage2', 'success': False, 'channelLoc': requestedChannel.channelLoc, 'ipAddress': str(ipaddress), 'message': 'Failed - No Matching Stage 1 Connection'}
            db.session.close()
            return returnMessage
    else:
        returnMessage = {'time': str(currentTime), 'request': 'Stage2', 'success': False, 'channelLoc': channelLoc, 'ipAddress': str(ipaddress), 'message': 'Failed - Passed Stage 1 Channel ID Does Not Match Any Known Channels'}
        db.session.close()
        return returnMessage

def rtmp_record_auth_check(channelLoc):

    sysSettings = cachedDbCalls.getSystemSettings()
    channelRequest = Channel.Channel.query.filter_by(channelLoc=channelLoc).first()
    currentTime = datetime.datetime.utcnow()

    if channelRequest is not None:
        userQuery = Sec.User.query.filter_by(id=channelRequest.owningUser).first()


        if channelRequest.record is True and sysSettings.allowRecording is True and userQuery.has_role("Recorder"):
            existingRecordingQuery = RecordedVideo.RecordedVideo.query.filter_by(channelID=channelRequest.id, pending=True).all()
            if existingRecordingQuery:
                for recording in existingRecordingQuery:
                    db.session.delete(recording)
                db.session.commit()

            streamID = None
            existingStream = Stream.Stream.query.filter_by(complete=False, linkedChannel=channelRequest.id).first()
            if existingStream is not None:
                streamID = existingStream.id

            newRecording = RecordedVideo.RecordedVideo(userQuery.id, channelRequest.id, channelRequest.channelName, channelRequest.topic, 0, "", currentTime, channelRequest.allowComments, False)
            newRecording.originalStreamID = streamID
            db.session.add(newRecording)
            db.session.commit()

            pendingVideo = RecordedVideo.RecordedVideo.query.filter_by(channelID=channelRequest.id, videoLocation="", pending=True).first()
            existingStream.recordedVideoId = pendingVideo.id
            db.session.commit()

            returnMessage = {'time': str(currentTime), 'request': 'RecordCheck', 'success': True, 'channelLoc': channelRequest.channelLoc, 'ipAddress': None, 'message': 'Success - Starting Recording'}
            return returnMessage
        else:
            returnMessage = {'time': str(currentTime), 'request': 'RecordCheck', 'success': False, 'channelLoc': channelRequest.channelLoc, 'ipAddress': None, 'message': 'Failed - Record Not Enabled or User Missing Recorder Role'}
            return returnMessage
    returnMessage = {'time': str(currentTime), 'request': 'RecordCheck', 'success': False, 'channelLoc': channelLoc, 'ipAddress': None, 'message': 'Failed - No Channel Exists'}
    return returnMessage

def rtmp_user_deauth_check(key, ipaddress):
    sysSettings = cachedDbCalls.getSystemSettings()

    currentTime = datetime.datetime.utcnow()

    authedStream = Stream.Stream.query.filter_by(active=True, complete=False, streamKey=key).all()

    channelRequest = Channel.Channel.query.filter_by(streamKey=key).first()

    if authedStream is not []:
        for stream in authedStream:

            pendingVideo = RecordedVideo.RecordedVideo.query.filter_by(channelID=channelRequest.id, videoLocation="", originalStreamID=stream.id).first()

            wasRecorded = False
            recordingID = None
            endTimestamp = datetime.datetime.utcnow()
            length = (endTimestamp - stream.startTimestamp).total_seconds()

            if pendingVideo is not None:
                pendingVideo.length = length
                pendingVideo.channelName = stream.streamName
                pendingVideo.views = stream.totalViewers
                pendingVideo.topic = stream.topic
                wasRecorded = True
                recordingID = pendingVideo.id

                db.session.commit()

                streamUpvotes = upvotes.streamUpvotes.query.filter_by(streamID=stream.id).all()
                for upvote in streamUpvotes:
                    newVideoUpvote = upvotes.videoUpvotes(upvote.userID, pendingVideo.id)
                    db.session.add(newVideoUpvote)
                db.session.commit()

            topicName = "Unknown"
            topicQuery = topics.topics.query.filter_by(id=stream.topic).first()
            if topicQuery is not None:
                topicName = topicQuery.name

            newStreamHistory = logs.streamHistory(stream.uuid, stream.channel.owningUser, stream.channel.owner.username, stream.linkedChannel, stream.channel.channelName, stream.streamName,
                                                  stream.startTimestamp, endTimestamp, stream.totalViewers, stream.get_upvotes(), wasRecorded, stream.topic, topicName, recordingID)
            db.session.add(newStreamHistory)
            db.session.commit()

            stream.endTimeStamp = currentTime
            stream.active = False
            stream.pending = False
            stream.complete = True
            db.session.commit()

            if channelRequest.imageLocation is None:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
            else:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + channelRequest.imageLocation)

            message_tasks.send_webhook.delay(channelRequest.id, 1, channelname=channelRequest.channelName,
                       channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(channelRequest.id)),
                       channeltopic=channelRequest.topic,
                       channelimage=channelImage, streamer=templateFilters.get_userName(channelRequest.owningUser),
                       channeldescription=str(channelRequest.description),
                       streamname=stream.streamName,
                       streamurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/view/" + channelRequest.channelLoc),
                       streamtopic=templateFilters.get_topicName(stream.topic),
                       streamimage=(sysSettings.siteProtocol + sysSettings.siteAddress + "/stream-thumb/" + str(channelRequest.channelLoc) + ".png"))
        returnMessage = {'time': str(currentTime), 'request': 'StreamClose', 'success': True, 'channelLoc': channelRequest.channelLoc, 'ipAddress': str(ipaddress), 'message': 'Success - Stream Closed'}
        db.session.close()
        return returnMessage
    else:
        returnMessage = {'time': str(currentTime), 'request': 'StreamClose', 'success': False, 'channelLoc': None, 'ipAddress': str(ipaddress), 'message': 'Failed - No Stream Listed Under Key'}
        db.session.close()
        return returnMessage

@celery.task(bind=True, max_retries=5)
def rtmp_rec_Complete_handler(self, channelLoc, path):
    try:
        sysSettings = cachedDbCalls.getSystemSettings()

        currentTime = datetime.datetime.utcnow()

        requestedChannel = Channel.Channel.query.filter_by(channelLoc=channelLoc).first()

        if requestedChannel is not None:

            pendingVideo = RecordedVideo.RecordedVideo.query.filter_by(channelID=requestedChannel.id, videoLocation="", pending=True).first()

            videoPath = path.replace('/tmp/', requestedChannel.channelLoc + '/')
            imagePath = videoPath.replace('.flv','.png')
            gifPath = videoPath.replace('.flv', '.gif')
            videoPath = videoPath.replace('.flv','.mp4')

            pendingVideo.thumbnailLocation = imagePath
            pendingVideo.videoLocation = videoPath
            pendingVideo.gifLocation = gifPath

            videos_root = current_app.config['WEB_ROOT'] + 'videos/'
            fullVidPath = videos_root + videoPath

            pendingVideo.pending = False

            if requestedChannel.autoPublish is True:
                pendingVideo.published = True
            else:
                pendingVideo.published = False

            db.session.commit()

            if requestedChannel.imageLocation is None:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
            else:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + requestedChannel.imageLocation)

            if requestedChannel.autoPublish is True:
                message_tasks.send_webhook.delay(requestedChannel.id, 6, channelname=requestedChannel.channelName,
                       channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(requestedChannel.id)),
                       channeltopic=templateFilters.get_topicName(requestedChannel.topic),
                       channelimage=channelImage, streamer=templateFilters.get_userName(requestedChannel.owningUser),
                       channeldescription=str(requestedChannel.description), videoname=pendingVideo.channelName,
                       videodate=pendingVideo.videoDate, videodescription=pendingVideo.description,videotopic=templateFilters.get_topicName(pendingVideo.topic),
                       videourl=(sysSettings.siteProtocol + sysSettings.siteAddress + '/play/' + str(pendingVideo.id)),
                       videothumbnail=(sysSettings.siteProtocol + sysSettings.siteAddress + '/videos/' + str(pendingVideo.thumbnailLocation)))

                subscriptionQuery = subscriptions.channelSubs.query.filter_by(channelID=requestedChannel.id).all()
                for sub in subscriptionQuery:
                    # Create Notification for Channel Subs
                    newNotification = notifications.userNotification(templateFilters.get_userName(requestedChannel.owningUser) + " has posted a new video to " + requestedChannel.channelName + " titled " + pendingVideo.channelName, '/play/' + str(pendingVideo.id),
                                                                     "/images/" + str(requestedChannel.owner.pictureLocation), sub.userID)
                    db.session.add(newNotification)
                db.session.commit()

                subsFunc.processSubscriptions(requestedChannel.id, sysSettings.siteName + " - " + requestedChannel.channelName + " has posted a new video",
                                 "<html><body><img src='" + sysSettings.siteProtocol + sysSettings.siteAddress + sysSettings.systemLogo + "'><p>Channel " + requestedChannel.channelName + " has posted a new video titled <u>" + pendingVideo.channelName +
                                 "</u> to the channel.</p><p>Click this link to watch<br><a href='" + sysSettings.siteProtocol + sysSettings.siteAddress + "/play/" + str(pendingVideo.id) + "'>" + pendingVideo.channelName + "</a></p>")

            while not os.path.exists(fullVidPath):
                time.sleep(1)

            returnMessage = {'time': str(currentTime), 'request': 'RecordingClose', 'success': True, 'channelLoc': requestedChannel.channelLoc, 'ipAddress': None, 'message': 'Success - Recorded Video Processing Complete'}
            db.session.close()
            return returnMessage
        else:
            returnMessage = {'time': str(currentTime), 'request': 'RecordingClose', 'success': False, 'channelLoc': channelLoc, 'ipAddress': None, 'message': 'Failed - Requested Channel Does Not Exist'}
            return returnMessage
    except Exception as ex:
        log.exception("Failed to process Recording Close - Attempt #" + str(self.request.retries) + " : " + str(ex))
        self.retry(countdown=3 ** self.request.retries)
