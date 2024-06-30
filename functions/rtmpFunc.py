import os
import time
import hashlib
import datetime
import logging
import pathlib

from celery import states
from celery.exceptions import Ignore
from flask import Blueprint, request, redirect, current_app, abort

from classes.shared import db, celery, cache
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
from functions import notifications as notificationFunctions
from functions import cachedDbCalls
from functions.scheduled_tasks import message_tasks

log = logging.getLogger("app.functions.rtmpFunctions")


def rtmp_stage1_streamkey_check(key, ipaddress):
    sysSettings = cachedDbCalls.getSystemSettings()

    channelRequest = cachedDbCalls.getChannelByStreamKey(key)

    currentTime = datetime.datetime.utcnow()

    if channelRequest is not None:
        userQuery = Sec.User.query.filter_by(id=channelRequest.owningUser).first()
        if userQuery is not None:
            if userQuery.has_role("Streamer"):

                if not userQuery.active:
                    returnMessage = {
                        "time": str(currentTime),
                        "request": "Stage1",
                        "success": False,
                        "channelLoc": channelRequest.channelLoc,
                        "type": None,
                        "ipAddress": str(ipaddress),
                        "message": "Unauthorized User - User has been disabled",
                    }
                    return returnMessage

                # Checks for is there are any existing live streams and terminates them
                existingStreamQuery = Stream.Stream.query.filter_by(
                    active=True, linkedChannel=channelRequest.id
                ).delete()

                db.session.commit()

                # Checks for is there are any pending live streams and terminates them
                existingStreamQuery = Stream.Stream.query.filter_by(
                    pending=True, linkedChannel=channelRequest.id
                ).delete()
                db.session.commit()

                defaultStreamName = templateFilters.normalize_date(str(currentTime))
                if channelRequest.defaultStreamName != "":
                    defaultStreamName = channelRequest.defaultStreamName

                newStream = Stream.Stream(
                    key, defaultStreamName, int(channelRequest.id), channelRequest.topic
                )
                db.session.add(newStream)
                db.session.commit()

                if sysSettings.adaptiveStreaming:
                    returnMessage = {
                        "time": str(currentTime),
                        "request": "Stage1",
                        "success": True,
                        "channelLoc": channelRequest.channelLoc,
                        "type": "adaptive",
                        "ipAddress": str(ipaddress),
                        "message": "Success - Passing to Stage 2 - Adaptive",
                    }
                    return returnMessage
                else:
                    returnMessage = {
                        "time": str(currentTime),
                        "request": "Stage1",
                        "success": True,
                        "channelLoc": channelRequest.channelLoc,
                        "type": "standard",
                        "ipAddress": str(ipaddress),
                        "message": "Success - Passing to Stage 2 - Standard",
                    }
                    return returnMessage

            else:
                returnMessage = {
                    "time": str(currentTime),
                    "request": "Stage1",
                    "success": False,
                    "channelLoc": channelRequest.channelLoc,
                    "type": None,
                    "ipAddress": str(ipaddress),
                    "message": "Unauthorized User - Missing Streamer Role",
                }
                db.session.close()
                return returnMessage
        else:
            returnMessage = {
                "time": str(currentTime),
                "request": "Stage1",
                "success": False,
                "channelLoc": channelRequest.channelLoc,
                "type": None,
                "ipAddress": str(ipaddress),
                "message": "Unauthorized User - No Such User",
            }
            db.session.close()
            return returnMessage
    else:
        returnedResult = {
            "time": str(currentTime),
            "request": "Stage1",
            "success": False,
            "channelLoc": None,
            "type": None,
            "ipAddress": str(ipaddress),
            "message": "Unauthorized Key",
        }
        log.warning(returnedResult)
        returnMessage = returnedResult
        db.session.close()
        return returnMessage


def rtmp_stage2_user_auth_check(channelLoc, ipaddress, authorizedRTMP):
    sysSettings = cachedDbCalls.getSystemSettings()

    currentTime = datetime.datetime.utcnow()

    requestedChannel = cachedDbCalls.getChannelByLoc(channelLoc)

    if requestedChannel is not None:
        authedStream = Stream.Stream.query.filter_by(
            pending=True, streamKey=requestedChannel.streamKey
        ).with_entities(Stream.Stream.id, Stream.Stream.streamName, Stream.Stream.topic).first()

        if authedStream is not None:

            currentViewers = int(
                xmpp.getChannelCounts(requestedChannel.channelLoc)
            )
            totalViewers = int(
                xmpp.getChannelCounts(requestedChannel.channelLoc)
            )

            authedStreamUpdate = Stream.Stream.query.filter_by(id=authedStream.id).update(dict(currentViewers=currentViewers, totalViewers=totalViewers, active=True, pending=False, rtmpServer=authorizedRTMP))
            db.session.commit()

            if requestedChannel.imageLocation is None:
                channelImage = (
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/static/img/video-placeholder.jpg"
                )
            else:
                channelImage = (
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/images/"
                    + requestedChannel.imageLocation
                )

            message_tasks.send_webhook.delay(
                requestedChannel.id,
                0,
                channelname=requestedChannel.channelName,
                channelurl=(
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/channel/"
                    + str(requestedChannel.id)
                ),
                channeltopic=requestedChannel.topic,
                channelimage=channelImage,
                streamer=templateFilters.get_userName(requestedChannel.owningUser),
                channeldescription=str(requestedChannel.description),
                streamname=authedStream.streamName,
                streamurl=(
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/view/"
                    + requestedChannel.channelLoc
                ),
                streamtopic=templateFilters.get_topicName(authedStream.topic),
                streamimage=(
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/stream-thumb/"
                    + requestedChannel.channelLoc
                    + ".png"
                ),
            )

            subscriptionQuery = (
                subscriptions.channelSubs.query.filter_by(channelID=requestedChannel.id)
                .with_entities(
                    subscriptions.channelSubs.id, subscriptions.channelSubs.userID
                )
                .all()
            )
            for sub in subscriptionQuery:
                # Create Notification for Channel Subs
                notificationFunctions.sendNotification(
                    templateFilters.get_userName(requestedChannel.owningUser)
                    + " has started a live stream in "
                    + requestedChannel.channelName,
                    "/view/" + str(requestedChannel.channelLoc),
                    "/images/"
                    + str(
                        templateFilters.get_pictureLocation(requestedChannel.owningUser)
                    ),
                    sub.userID,
                )
            try:
                subsFunc.processSubscriptions(
                    requestedChannel.id,
                    sysSettings.siteName
                    + " - "
                    + requestedChannel.channelName
                    + " has started a stream",
                    "<html><body><img src='"
                    + sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + sysSettings.systemLogo
                    + "'><p>Channel "
                    + requestedChannel.channelName
                    + " has started a new video stream.</p><p>Click this link to watch<br><a href='"
                    + sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/view/"
                    + str(requestedChannel.channelLoc)
                    + "'>"
                    + requestedChannel.channelName
                    + "</a></p>",
                    "stream",
                )
            except:
                system.newLog(
                    0, "Subscriptions Failed due to possible misconfiguration"
                )

            returnMessage = {
                "time": str(currentTime),
                "request": "Stage2",
                "success": True,
                "channelLoc": requestedChannel.channelLoc,
                "ipAddress": str(ipaddress),
                "adaptive": sysSettings.adaptiveStreaming,
                "message": "Success - Stream Authenticated & Initialized",
            }
            db.session.close()
            return returnMessage
        else:
            returnMessage = {
                "time": str(currentTime),
                "request": "Stage2",
                "success": False,
                "channelLoc": requestedChannel.channelLoc,
                "ipAddress": str(ipaddress),
                "message": "Failed - No Matching Stage 1 Connection",
            }
            db.session.close()
            return returnMessage
    else:
        returnMessage = {
            "time": str(currentTime),
            "request": "Stage2",
            "success": False,
            "channelLoc": channelLoc,
            "ipAddress": str(ipaddress),
            "message": "Failed - Passed Stage 1 Channel ID Does Not Match Any Known Channels",
        }
        db.session.close()
        return returnMessage


def rtmp_record_auth_check(channelLoc):

    sysSettings = cachedDbCalls.getSystemSettings()
    channelRequest = cachedDbCalls.getChannelByLoc(channelLoc)
    currentTime = datetime.datetime.utcnow()

    if channelRequest is not None:
        userQuery = Sec.User.query.filter_by(id=channelRequest.owningUser).first()

        if (
            channelRequest.record is True
            and sysSettings.allowRecording is True
            and userQuery.has_role("Recorder")
        ):
            existingRecordingQuery = RecordedVideo.RecordedVideo.query.filter_by(
                channelID=channelRequest.id, pending=True, videoLocation=""
            ).delete()
            db.session.commit()

            streamID = None
            existingStream = (
                Stream.Stream.query.filter_by(
                    complete=False, linkedChannel=channelRequest.id
                )
                .with_entities(Stream.Stream.id)
                .first()
            )

            if existingStream is not None:
                streamID = existingStream.id

                newRecording = RecordedVideo.RecordedVideo(
                    userQuery.id,
                    channelRequest.id,
                    channelRequest.channelName,
                    channelRequest.topic,
                    0,
                    "",
                    currentTime,
                    channelRequest.allowComments,
                    False,
                )
                newRecording.originalStreamID = streamID
                db.session.add(newRecording)
                db.session.commit()

                pendingVideo = (
                    RecordedVideo.RecordedVideo.query.filter_by(
                        channelID=channelRequest.id, videoLocation="", pending=True
                    )
                    .with_entities(RecordedVideo.RecordedVideo.id)
                    .first()
                )

                StreamQueryUpdate = Stream.Stream.query.filter_by(
                    id=existingStream.id
                ).update(dict(recordedVideoId=pendingVideo.id))

                db.session.commit()

                returnMessage = {
                    "time": str(currentTime),
                    "request": "RecordCheck",
                    "success": True,
                    "channelLoc": channelRequest.channelLoc,
                    "ipAddress": None,
                    "message": "Success - Starting Recording",
                }
                return returnMessage
            else:
                returnMessage = {
                    "time": str(currentTime),
                    "request": "RecordCheck",
                    "success": False,
                    "channelLoc": channelRequest.channelLoc,
                    "ipAddress": None,
                    "message": "Failed - No Existing Stream for Recording",
                }
                return returnMessage
        else:
            returnMessage = {
                "time": str(currentTime),
                "request": "RecordCheck",
                "success": False,
                "channelLoc": channelRequest.channelLoc,
                "ipAddress": None,
                "message": "Failed - Record Not Enabled or User Missing Recorder Role",
            }
            return returnMessage
    returnMessage = {
        "time": str(currentTime),
        "request": "RecordCheck",
        "success": False,
        "channelLoc": channelLoc,
        "ipAddress": None,
        "message": "Failed - No Channel Exists",
    }
    return returnMessage


def rtmp_user_deauth_check(key, ipaddress):
    sysSettings = cachedDbCalls.getSystemSettings()

    currentTime = datetime.datetime.utcnow()

    closingStreams = (
        Stream.Stream.query.filter_by(active=True, complete=False, streamKey=key)
        .with_entities(Stream.Stream.id, Stream.Stream.uuid)
        .all()
    )
    closingStreamIds = []
    for stream in closingStreams:
        closingStreamIds.append(stream.id)
    authedStream = Stream.Stream.query.filter_by(
        active=True, complete=False, streamKey=key
    ).update(dict(endTimeStamp=currentTime, active=False, pending=False, complete=True))

    db.session.commit()

    channelRequest = cachedDbCalls.getChannelByStreamKey(key)

    for streamId in closingStreamIds:
        authedStream = (
            Stream.Stream.query.filter_by(id=streamId)
            .with_entities(
                Stream.Stream.id,
                Stream.Stream.uuid,
                Stream.Stream.startTimestamp,
                Stream.Stream.endTimeStamp,
                Stream.Stream.linkedChannel,
                Stream.Stream.streamKey,
                Stream.Stream.streamName,
                Stream.Stream.topic,
                Stream.Stream.currentViewers,
                Stream.Stream.totalViewers,
                Stream.Stream.active,
                Stream.Stream.pending,
                Stream.Stream.complete,
                Stream.Stream.complete,
                Stream.Stream.recordedVideoId,
                Stream.Stream.rtmpServer,
            )
            .all()
        )
        if authedStream is not []:
            for stream in authedStream:
                wasRecorded = False
                recordingID = None
                endTimestamp = datetime.datetime.utcnow()
                length = (endTimestamp - stream.startTimestamp).total_seconds()

                pendingVideo = RecordedVideo.RecordedVideo.query.filter_by(
                    channelID=channelRequest.id, originalStreamID=stream.id
                ).first()

                if pendingVideo is not None:
                    pendingVideo.length = length
                    pendingVideo.channelName = stream.streamName
                    pendingVideo.views = stream.totalViewers
                    pendingVideo.topic = stream.topic
                    wasRecorded = True
                    recordingID = pendingVideo.id

                    # db.session.commit()

                    streamUpvotes = upvotes.streamUpvotes.query.filter_by(
                        streamID=stream.id
                    ).all()
                    for upvote in streamUpvotes:
                        newVideoUpvote = upvotes.videoUpvotes(
                            upvote.userID, pendingVideo.id
                        )
                        db.session.add(newVideoUpvote)
                    # db.session.commit()

                topicName = "Unknown"
                topicQuery = topics.topics.query.filter_by(id=stream.topic).first()
                if topicQuery is not None:
                    topicName = topicQuery.name

                channelOwnerUserName = templateFilters.get_userName(
                    channelRequest.owningUser
                )

                newStreamHistory = logs.streamHistory(
                    stream.uuid,
                    channelRequest.owningUser,
                    channelOwnerUserName,
                    stream.linkedChannel,
                    channelRequest.channelName,
                    stream.streamName,
                    stream.startTimestamp,
                    endTimestamp,
                    stream.totalViewers,
                    templateFilters.get_Stream_Upvotes_Filter(stream.id),
                    wasRecorded,
                    stream.topic,
                    topicName,
                    recordingID,
                )
                db.session.add(newStreamHistory)
                # db.session.commit()

                if channelRequest.imageLocation is None:
                    channelImage = (
                        sysSettings.siteProtocol
                        + sysSettings.siteAddress
                        + "/static/img/video-placeholder.jpg"
                    )
                else:
                    channelImage = (
                        sysSettings.siteProtocol
                        + sysSettings.siteAddress
                        + "/images/"
                        + channelRequest.imageLocation
                    )

                message_tasks.send_webhook.delay(
                    channelRequest.id,
                    1,
                    channelname=channelRequest.channelName,
                    channelurl=(
                        sysSettings.siteProtocol
                        + sysSettings.siteAddress
                        + "/channel/"
                        + str(channelRequest.id)
                    ),
                    channeltopic=channelRequest.topic,
                    channelimage=channelImage,
                    streamer=templateFilters.get_userName(channelRequest.owningUser),
                    channeldescription=str(channelRequest.description),
                    streamname=stream.streamName,
                    streamurl=(
                        sysSettings.siteProtocol
                        + sysSettings.siteAddress
                        + "/view/"
                        + channelRequest.channelLoc
                    ),
                    streamtopic=templateFilters.get_topicName(stream.topic),
                    streamimage=(
                        sysSettings.siteProtocol
                        + sysSettings.siteAddress
                        + "/stream-thumb/"
                        + str(channelRequest.channelLoc)
                        + ".png"
                    ),
                )
            returnMessage = {
                "time": str(currentTime),
                "request": "StreamClose",
                "success": True,
                "channelLoc": channelRequest.channelLoc,
                "ipAddress": str(ipaddress),
                "message": "Success - Stream Closed",
            }
            db.session.commit()
            db.session.close()
            return returnMessage
        else:
            returnMessage = {
                "time": str(currentTime),
                "request": "StreamClose",
                "success": False,
                "channelLoc": None,
                "ipAddress": str(ipaddress),
                "message": "Failed - No Stream Listed Under Key",
            }
            db.session.commit()
            db.session.close()
            return returnMessage


@celery.task(bind=True, max_retries=100)
def rtmp_rec_Complete_handler(self, channelLoc, path, pendingVideoID=None):
    try:
        sysSettings = cachedDbCalls.getSystemSettings()

        currentTime = datetime.datetime.utcnow()

        requestedChannel = cachedDbCalls.getChannelByLoc(channelLoc)

        if requestedChannel is not None:
            if pendingVideoID != None:
                pendingVideo = RecordedVideo.RecordedVideo.query.filter_by(
                    channelID=requestedChannel.id, id=pendingVideoID, pending=True
                ).with_entities(
                    RecordedVideo.RecordedVideo.id,
                    RecordedVideo.RecordedVideo.channelName,
                    RecordedVideo.RecordedVideo.videoDate,
                    RecordedVideo.RecordedVideo.description,
                    RecordedVideo.RecordedVideo.topic,
                    RecordedVideo.RecordedVideo.thumbnailLocation
                ).first()
            else:
                pendingVideo = RecordedVideo.RecordedVideo.query.filter_by(
                    channelID=requestedChannel.id, videoLocation="", pending=True
                ).with_entities(
                    RecordedVideo.RecordedVideo.id,
                    RecordedVideo.RecordedVideo.channelName,
                    RecordedVideo.RecordedVideo.videoDate,
                    RecordedVideo.RecordedVideo.description,
                    RecordedVideo.RecordedVideo.topic,
                    RecordedVideo.RecordedVideo.thumbnailLocation
                ).first()
            
            if pendingVideo is None:
                returnMessage = {
                    "time": str(currentTime),
                    "request": "RecordingClose",
                    "success": False,
                    "channelLoc": requestedChannel.channelLoc,
                    "ipAddress": None,
                    "message": "Failure - No Pending Video Exists to Close",
                }   
                db.session.close()
                return returnMessage

            pendingPath = path.replace(
                "/tmp/", current_app.config["WEB_ROOT"] + "pending/"
            )
            pathlibPath = pathlib.Path(pendingPath)
            while pathlibPath.is_file() == False:
                time.sleep(2)

            fileName = pathlibPath.name

            workingVideoID = pendingVideo.id
            videoChannelName = pendingVideo.channelName

            updatePending = RecordedVideo.RecordedVideo.query.filter_by(id=pendingVideo.id).update(dict(videoLocation=pendingPath))

            channelTuple = (requestedChannel.id, requestedChannel.channelLoc)
            db.session.commit()

            notificationFunctions.sendNotification(f"{videoChannelName} has started processing.", f"/play/{workingVideoID}", f"/images/{templateFilters.get_pictureLocation(requestedChannel.owningUser)}", requestedChannel.owningUser)

            results = videoFunc.processStreamVideo(fileName, channelTuple[1])

            # If File does not exist in expected destination, Raise Task Failure
            if results == False:
                self.update_state(
                    state=states.FAILURE, meta="FFMPEG Processing Failure"
                )
                raise Ignore()

            requestedChannel = cachedDbCalls.getChannelByLoc(
                requestedChannel.channelLoc
            )

            cache.delete_memoized(cachedDbCalls.getChannelVideos, requestedChannel.id)
            cache.delete_memoized(cachedDbCalls.getAllVideo_View, requestedChannel.id)

            videoPath = path.replace("/var/www/pending/", channelTuple[1] + "/")
            imagePath = videoPath.replace(".flv", ".png")
            gifPath = videoPath.replace(".flv", ".gif")
            videoPath = videoPath.replace(".flv", ".mp4")

            videos_root = current_app.config["WEB_ROOT"] + "videos/"
            fullVidPath = videos_root + videoPath


            if requestedChannel.autoPublish is True:
                updateVideo = RecordedVideo.RecordedVideo.query.filter_by(id=workingVideoID).update(dict(thumbnailLocation=imagePath, videoLocation=videoPath, gifLocation=gifPath, pending=False, published=True))
                notificationFunctions.sendNotification(f"{videoChannelName} has finished processing and has been published.", f"/play/{workingVideoID}", f"/images/{templateFilters.get_pictureLocation(requestedChannel.owningUser)}", requestedChannel.owningUser)
            else:
                updateVideo = RecordedVideo.RecordedVideo.query.filter_by(id=workingVideoID).update(dict(thumbnailLocation=imagePath, videoLocation=videoPath, gifLocation=gifPath, pending=False, published=False))
                notificationFunctions.sendNotification(f"{videoChannelName} has finished processing and is available in the Channel Settings Page.", f"/play/{workingVideoID}", f"/images/{templateFilters.get_pictureLocation(requestedChannel.owningUser)}", requestedChannel.owningUser)

            db.session.commit()

            pendingVideo = RecordedVideo.RecordedVideo.query.filter_by(
                channelID=requestedChannel.id, id=pendingVideoID, pending=True
                ).with_entities(
                    RecordedVideo.RecordedVideo.id,
                    RecordedVideo.RecordedVideo.channelName,
                    RecordedVideo.RecordedVideo.videoDate,
                    RecordedVideo.RecordedVideo.description,
                    RecordedVideo.RecordedVideo.topic,
                    RecordedVideo.RecordedVideo.thumbnailLocation
                ).first()

            if requestedChannel.imageLocation is None:
                channelImage = (
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/static/img/video-placeholder.jpg"
                )
            else:
                channelImage = (
                    sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/images/"
                    + requestedChannel.imageLocation
                )

            if requestedChannel.autoPublish is True:
                message_tasks.send_webhook.delay(
                    requestedChannel.id,
                    6,
                    channelname=requestedChannel.channelName,
                    channelurl=(
                        sysSettings.siteProtocol
                        + sysSettings.siteAddress
                        + "/channel/"
                        + str(requestedChannel.id)
                    ),
                    channeltopic=templateFilters.get_topicName(requestedChannel.topic),
                    channelimage=channelImage,
                    streamer=templateFilters.get_userName(requestedChannel.owningUser),
                    channeldescription=str(requestedChannel.description),
                    videoname=pendingVideo.channelName,
                    videodate=pendingVideo.videoDate,
                    videodescription=pendingVideo.description,
                    videotopic=templateFilters.get_topicName(pendingVideo.topic),
                    videourl=(
                        sysSettings.siteProtocol
                        + sysSettings.siteAddress
                        + "/play/"
                        + str(pendingVideo.id)
                    ),
                    videothumbnail=(
                        sysSettings.siteProtocol
                        + sysSettings.siteAddress
                        + "/videos/"
                        + str(pendingVideo.thumbnailLocation)
                    ),
                )

                subscriptionQuery = subscriptions.channelSubs.query.filter_by(
                    channelID=requestedChannel.id
                ).all()
                for sub in subscriptionQuery:
                    # Create Notification for Channel Subs
                    notificationFunctions.sendNotification(
                        templateFilters.get_userName(requestedChannel.owningUser)
                        + " has posted a new video to "
                        + requestedChannel.channelName
                        + " titled "
                        + pendingVideo.channelName,
                        "/play/" + str(pendingVideo.id),
                        "/images/"
                        + str(
                            templateFilters.get_pictureLocation(
                                requestedChannel.owningUser
                            )
                        ),
                        sub.userID,
                    )
                    
                subsFunc.processSubscriptions(
                    requestedChannel.id,
                    sysSettings.siteName
                    + " - "
                    + requestedChannel.channelName
                    + " has posted a new video",
                    "<html><body><img src='"
                    + sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + sysSettings.systemLogo
                    + "'><p>Channel "
                    + requestedChannel.channelName
                    + " has posted a new video titled <u>"
                    + pendingVideo.channelName
                    + "</u> to the channel.</p><p>Click this link to watch<br><a href='"
                    + sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/play/"
                    + str(pendingVideo.id)
                    + "'>"
                    + pendingVideo.channelName
                    + "</a></p>",
                    "video",
                )

            while not os.path.exists(fullVidPath):
                time.sleep(1)

            returnMessage = {
                "time": str(currentTime),
                "request": "RecordingClose",
                "success": True,
                "channelLoc": requestedChannel.channelLoc,
                "ipAddress": None,
                "message": "Success - Recorded Video Processing Complete",
            }
            db.session.close()
            return returnMessage
        else:
            returnMessage = {
                "time": str(currentTime),
                "request": "RecordingClose",
                "success": False,
                "channelLoc": channelLoc,
                "ipAddress": None,
                "message": "Failed - Requested Channel Does Not Exist",
            }
            return returnMessage
    except Exception as ex:
        log.exception(
            "Failed to process Recording Close - Attempt #"
            + str(self.request.retries)
            + " : "
            + str(ex)
        )
        self.retry(countdown=3**self.request.retries)
