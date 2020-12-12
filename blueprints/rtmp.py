import os
import time
import hashlib
import datetime
import socket
import subprocess

from flask import Blueprint, request, redirect, current_app, abort

from classes.shared import db
from classes import Sec
from classes import RecordedVideo
from classes import subscriptions
from classes import notifications
from classes import Channel
from classes import Stream
from classes import settings
from classes import upvotes

from functions import webhookFunc
from functions import system
from functions import templateFilters
from functions import subsFunc
from functions import videoFunc
from functions import xmpp

from globals import globalvars
from app import coreNginxRTMPAddress

rtmp_bp = Blueprint('rtmp', __name__)

@rtmp_bp.route('/auth-key', methods=['POST'])
def streamkey_check():
    sysSettings = settings.settings.query.first()

    key = request.form['name']
    ipaddress = request.form['addr']

    channelRequest = Channel.Channel.query.filter_by(streamKey=key).first()

    currentTime = datetime.datetime.now()

    if channelRequest is not None:
        userQuery = Sec.User.query.filter_by(id=channelRequest.owningUser).first()
        if userQuery is not None:
            if userQuery.has_role('Streamer'):

                if not userQuery.active:
                    returnMessage = {'time': str(currentTime), 'status': 'Unauthorized User - User has been Disabled', 'key': str(key), 'ipAddress': str(ipaddress)}
                    print(returnMessage)
                    return abort(400)

                returnMessage = {'time': str(currentTime), 'status': 'Successful Key Auth', 'key': str(key), 'channelName': str(channelRequest.channelName), 'userName': str(channelRequest.owningUser), 'ipAddress': str(ipaddress)}
                print(returnMessage)

                #validAddress = system.formatSiteAddress(sysSettings.siteAddress)

                existingStreamQuery = Stream.Stream.query.filter_by(linkedChannel=channelRequest.id).all()
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
                    return redirect('rtmp://' + coreNginxRTMPAddress + '/stream-data-adapt/' + channelRequest.channelLoc, code=302)
                else:
                    return redirect('rtmp://' + coreNginxRTMPAddress + '/stream-data/' + channelRequest.channelLoc, code=302)

            else:
                returnMessage = {'time': str(currentTime), 'status': 'Unauthorized User - Missing Streamer Role', 'key': str(key), 'ipAddress': str(ipaddress)}
                print(returnMessage)
                db.session.close()
                return abort(400)
        else:
            returnMessage = {'time': str(currentTime), 'status': 'Unauthorized User - No Such User', 'key': str(key), 'ipAddress': str(ipaddress)}
            print(returnMessage)
            db.session.close()
            return abort(400)
    else:
        returnMessage = {'time': str(currentTime), 'status': 'Failed Key Auth', 'key':str(key), 'ipAddress': str(ipaddress)}
        print(returnMessage)
        db.session.close()
        return abort(400)

@rtmp_bp.route('/auth-user', methods=['POST'])
def user_auth_check():
    sysSettings = settings.settings.query.first()

    key = request.form['name']
    ipaddress = request.form['addr']

    requestedChannel = Channel.Channel.query.filter_by(channelLoc=key).first()

    if requestedChannel is not None:
        authedStream = Stream.Stream.query.filter_by(streamKey=requestedChannel.streamKey).first()

        if authedStream is not None:

            authedStream.currentViewers = int(xmpp.getChannelCounts(requestedChannel.channelLoc))
            authedStream.totalViewers = int(xmpp.getChannelCounts(requestedChannel.channelLoc))
            db.session.commit()

            returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Successful Channel Auth', 'key': str(requestedChannel.streamKey), 'channelName': str(requestedChannel.channelName), 'ipAddress': str(ipaddress)}
            print(returnMessage)

            if requestedChannel.imageLocation is None:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
            else:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + requestedChannel.imageLocation)

            webhookFunc.runWebhook(requestedChannel.id, 0, channelname=requestedChannel.channelName, channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(requestedChannel.id)), channeltopic=requestedChannel.topic,
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

            inputLocation = "rtmp://" + coreNginxRTMPAddress + ":1935/live/" + requestedChannel.channelLoc

            # Begin RTMP Restream Function
            if requestedChannel.restreamDestinations != []:
                globalvars.restreamSubprocesses[requestedChannel.channelLoc] = []
                for rtmpRestream in requestedChannel.restreamDestinations:
                    if rtmpRestream.enabled == True:
                        p = subprocess.Popen(["ffmpeg", "-i", inputLocation, "-c", "copy", "-f", "flv", rtmpRestream.url, "-c:v", "libx264", "-maxrate", str(sysSettings.restreamMaxBitrate) + "k", "-bufsize", "6000k", "-c:a", "aac", "-b:a", "160k", "-ac", "2"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        globalvars.restreamSubprocesses[requestedChannel.channelLoc].append(p)

            # Start OSP Edge Nodes
            ospEdgeNodeQuery = settings.edgeStreamer.query.filter_by(active=True).all()
            if ospEdgeNodeQuery is not []:
                globalvars.edgeRestreamSubprocesses[requestedChannel.channelLoc] = []

                for node in ospEdgeNodeQuery:
                    if node.address != sysSettings.siteAddress:
                        subprocessConstructor = ["ffmpeg", "-i", inputLocation, "-c", "copy"]
                        subprocessConstructor.append("-f")
                        subprocessConstructor.append("flv")
                        if sysSettings.adaptiveStreaming:
                            subprocessConstructor.append("rtmp://" + node.address + "/stream-data-adapt/" + requestedChannel.channelLoc)
                        else:
                            subprocessConstructor.append("rtmp://" + node.address + "/stream-data/" + requestedChannel.channelLoc)

                        p = subprocess.Popen(subprocessConstructor, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        globalvars.edgeRestreamSubprocesses[requestedChannel.channelLoc].append(p)

            db.session.close()
            return 'OK'
        else:
            returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Failed Channel Auth. No Authorized Stream Key', 'channelName': str(key), 'ipAddress': str(ipaddress)}
            print(returnMessage)
            db.session.close()
            return abort(400)
    else:
        returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Failed Channel Auth. Channel Loc does not match Channel', 'channelName': str(key), 'ipAddress': str(ipaddress)}
        print(returnMessage)
        db.session.close()
        return abort(400)

@rtmp_bp.route('/auth-record', methods=['POST'])
def record_auth_check():
    key = request.form['name']
    sysSettings = settings.settings.query.first()
    channelRequest = Channel.Channel.query.filter_by(channelLoc=key).first()
    currentTime = datetime.datetime.now()

    if channelRequest is not None:
        userQuery = Sec.User.query.filter_by(id=channelRequest.owningUser).first()

        if channelRequest.record is True and sysSettings.allowRecording is True and userQuery.has_role("Recorder"):
            existingRecordingQuery = RecordedVideo.RecordedVideo.query.filter_by(channelID=channelRequest.id, pending=True).all()
            if existingRecordingQuery:
                for recording in existingRecordingQuery:
                    db.session.delete(recording)
                    db.session.commit()

            newRecording = RecordedVideo.RecordedVideo(userQuery.id, channelRequest.id, channelRequest.channelName, channelRequest.topic, 0, "", currentTime, channelRequest.allowComments, False)
            db.session.add(newRecording)
            db.session.commit()

            return 'OK'
    return abort(400)

@rtmp_bp.route('/deauth-user', methods=['POST'])
def user_deauth_check():
    sysSettings = settings.settings.query.first()

    key = request.form['name']
    ipaddress = request.form['addr']

    authedStream = Stream.Stream.query.filter_by(streamKey=key).all()

    channelRequest = Channel.Channel.query.filter_by(streamKey=key).first()

    if authedStream is not []:
        for stream in authedStream:
            streamUpvotes = upvotes.streamUpvotes.query.filter_by(streamID=stream.id).all()
            pendingVideo = RecordedVideo.RecordedVideo.query.filter_by(channelID=channelRequest.id, videoLocation="", pending=True).first()

            if pendingVideo is not None:
                pendingVideo.channelName = stream.streamName
                pendingVideo.views = stream.totalViewers
                pendingVideo.topic = stream.topic

                for upvote in streamUpvotes:
                    newVideoUpvote = upvotes.videoUpvotes(upvote.userID, pendingVideo.id)
                    db.session.add(newVideoUpvote)
                db.session.commit()

            for vid in streamUpvotes:
                db.session.delete(vid)
            db.session.delete(stream)
            db.session.commit()

            # End RTMP Restream Function
            if channelRequest.restreamDestinations != []:
                if channelRequest.channelLoc in globalvars.restreamSubprocesses:
                    for restream in globalvars.restreamSubprocesses[channelRequest.channelLoc]:
                        #p = globalvars.restreamSubprocesses[channelRequest.channelLoc][restream]
                        restream.kill()
                try:
                    del globalvars.restreamSubprocesses[channelRequest.channelLoc]
                except KeyError:
                    pass

            if channelRequest.channelLoc in globalvars.edgeRestreamSubprocesses:
                for p in globalvars.edgeRestreamSubprocesses[channelRequest.channelLoc]:
                    p.kill()
                try:
                    del globalvars.edgeRestreamSubprocesses[channelRequest.channelLoc]
                except KeyError:
                    pass

            returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Stream Closed', 'key': str(key), 'channelName': str(channelRequest.channelName), 'userName':str(channelRequest.owningUser), 'ipAddress': str(ipaddress)}

            print(returnMessage)

            if channelRequest.imageLocation is None:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
            else:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + channelRequest.imageLocation)

            webhookFunc.runWebhook(channelRequest.id, 1, channelname=channelRequest.channelName,
                       channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(channelRequest.id)),
                       channeltopic=channelRequest.topic,
                       channelimage=channelImage, streamer=templateFilters.get_userName(channelRequest.owningUser),
                       channeldescription=str(channelRequest.description),
                       streamname=stream.streamName,
                       streamurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/view/" + channelRequest.channelLoc),
                       streamtopic=templateFilters.get_topicName(stream.topic),
                       streamimage=(sysSettings.siteProtocol + sysSettings.siteAddress + "/stream-thumb/" + str(channelRequest.channelLoc) + ".png"))
        return 'OK'
    else:
        returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Stream Closure Failure - No Such Stream', 'key': str(key), 'ipAddress': str(ipaddress)}
        print(returnMessage)
        db.session.close()
        return abort(400)


@rtmp_bp.route('/deauth-record', methods=['POST'])
def rec_Complete_handler():
    key = request.form['name']
    path = request.form['path']

    sysSettings = settings.settings.query.first()

    requestedChannel = Channel.Channel.query.filter_by(channelLoc=key).first()

    pendingVideo = RecordedVideo.RecordedVideo.query.filter_by(channelID=requestedChannel.id, videoLocation="", pending=True).first()

    videoPath = path.replace('/tmp/',requestedChannel.channelLoc + '/')
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
        webhookFunc.runWebhook(requestedChannel.id, 6, channelname=requestedChannel.channelName,
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

    if os.path.isfile(fullVidPath):
        pendingVideo.length = videoFunc.getVidLength(fullVidPath)
        db.session.commit()

    db.session.close()
    return 'OK'