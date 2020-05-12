import hashlib

from flask import Blueprint, request, url_for, render_template, redirect, current_app, send_from_directory, abort
from flask_security import current_user, login_required
from sqlalchemy.sql.expression import func

from classes.shared import db
from classes import Sec
from classes import RecordedVideo
from classes import subscriptions
from classes import topics
from classes import notifications
from classes import Channel
from classes import Stream
from classes import settings

from functions import themes
from functions import system
from functions import securityFunc

root_bp = Blueprint('root', __name__)


@root_bp.route('/')
def main_page():

    firstRunCheck = system.check_existing_settings()

    if firstRunCheck is False:
        return render_template('/firstrun.html')

    else:
        sysSettings = settings.settings.query.first()
        activeStreams = Stream.Stream.query.order_by(Stream.Stream.currentViewers).all()

        recordedQuery = None
        clipQuery = None

        # Sort by Most Views
        if sysSettings.sortMainBy == 0:
            recordedQuery = RecordedVideo.RecordedVideo.query.filter_by(pending=False, published=True) \
                .join(Channel.Channel, RecordedVideo.RecordedVideo.channelID == Channel.Channel.id) \
                .join(Sec.User, RecordedVideo.RecordedVideo.owningUser == Sec.User.id) \
                .with_entities(RecordedVideo.RecordedVideo.id, RecordedVideo.RecordedVideo.owningUser,
                               RecordedVideo.RecordedVideo.views, RecordedVideo.RecordedVideo.length,
                               RecordedVideo.RecordedVideo.thumbnailLocation, RecordedVideo.RecordedVideo.channelName,
                               RecordedVideo.RecordedVideo.topic, RecordedVideo.RecordedVideo.videoDate,
                               Sec.User.pictureLocation, Channel.Channel.protected,
                               Channel.Channel.channelName.label('ChanName')) \
                .order_by(RecordedVideo.RecordedVideo.views.desc()).limit(16)

            clipQuery = RecordedVideo.Clips.query.filter_by(published=True) \
                .join(RecordedVideo.RecordedVideo, RecordedVideo.Clips.parentVideo == RecordedVideo.RecordedVideo.id) \
                .join(Channel.Channel, Channel.Channel.id == RecordedVideo.RecordedVideo.channelID) \
                .join(Sec.User, Sec.User.id == Channel.Channel.owningUser) \
                .with_entities(RecordedVideo.Clips.id, RecordedVideo.Clips.thumbnailLocation,
                               Channel.Channel.owningUser, RecordedVideo.Clips.views, RecordedVideo.Clips.length,
                               RecordedVideo.Clips.clipName, Channel.Channel.protected, Channel.Channel.channelName,
                               RecordedVideo.RecordedVideo.topic, RecordedVideo.RecordedVideo.videoDate,
                               Sec.User.pictureLocation) \
                .order_by(RecordedVideo.Clips.views.desc()).limit(16)
        # Sort by Most Recent
        elif sysSettings.sortMainBy == 1:
            recordedQuery = RecordedVideo.RecordedVideo.query.filter_by(pending=False, published=True) \
                .join(Channel.Channel, RecordedVideo.RecordedVideo.channelID == Channel.Channel.id) \
                .join(Sec.User, RecordedVideo.RecordedVideo.owningUser == Sec.User.id) \
                .with_entities(RecordedVideo.RecordedVideo.id, RecordedVideo.RecordedVideo.owningUser,
                               RecordedVideo.RecordedVideo.views, RecordedVideo.RecordedVideo.length,
                               RecordedVideo.RecordedVideo.thumbnailLocation, RecordedVideo.RecordedVideo.channelName,
                               RecordedVideo.RecordedVideo.topic, RecordedVideo.RecordedVideo.videoDate,
                               Sec.User.pictureLocation, Channel.Channel.protected,
                               Channel.Channel.channelName.label('ChanName')) \
                .order_by(RecordedVideo.RecordedVideo.videoDate.desc()).limit(16)

            clipQuery = RecordedVideo.Clips.query.filter_by(published=True) \
                .join(RecordedVideo.RecordedVideo, RecordedVideo.Clips.parentVideo == RecordedVideo.RecordedVideo.id) \
                .join(Channel.Channel, Channel.Channel.id == RecordedVideo.RecordedVideo.channelID) \
                .join(Sec.User, Sec.User.id == Channel.Channel.owningUser) \
                .with_entities(RecordedVideo.Clips.id, RecordedVideo.Clips.thumbnailLocation,
                               Channel.Channel.owningUser, RecordedVideo.Clips.views, RecordedVideo.Clips.length,
                               RecordedVideo.Clips.clipName, Channel.Channel.protected, Channel.Channel.channelName,
                               RecordedVideo.RecordedVideo.topic, RecordedVideo.RecordedVideo.videoDate,
                               Sec.User.pictureLocation) \
                .order_by(RecordedVideo.RecordedVideo.videoDate.desc()).limit(16)
        # Sort by Random
        elif sysSettings.sortMainBy == 2:
            recordedQuery = RecordedVideo.RecordedVideo.query.filter_by(pending=False, published=True)\
                .join(Channel.Channel, RecordedVideo.RecordedVideo.channelID == Channel.Channel.id)\
                .join(Sec.User, RecordedVideo.RecordedVideo.owningUser == Sec.User.id)\
                .with_entities(RecordedVideo.RecordedVideo.id, RecordedVideo.RecordedVideo.owningUser, RecordedVideo.RecordedVideo.views, RecordedVideo.RecordedVideo.length, RecordedVideo.RecordedVideo.thumbnailLocation, RecordedVideo.RecordedVideo.channelName, RecordedVideo.RecordedVideo.topic, RecordedVideo.RecordedVideo.videoDate, Sec.User.pictureLocation, Channel.Channel.protected, Channel.Channel.channelName.label('ChanName'))\
                .order_by(func.random()).limit(16)

            clipQuery = RecordedVideo.Clips.query.filter_by(published=True)\
                .join(RecordedVideo.RecordedVideo, RecordedVideo.Clips.parentVideo == RecordedVideo.RecordedVideo.id)\
                .join(Channel.Channel, Channel.Channel.id==RecordedVideo.RecordedVideo.channelID)\
                .join(Sec.User, Sec.User.id == Channel.Channel.owningUser)\
                .with_entities(RecordedVideo.Clips.id, RecordedVideo.Clips.thumbnailLocation, Channel.Channel.owningUser, RecordedVideo.Clips.views, RecordedVideo.Clips.length, RecordedVideo.Clips.clipName, Channel.Channel.protected, Channel.Channel.channelName, RecordedVideo.RecordedVideo.topic, RecordedVideo.RecordedVideo.videoDate, Sec.User.pictureLocation)\
                .order_by(func.random()).limit(16)
        # Fall Through - Sort by Views
        else:
            if sysSettings.sortMainBy == 0:
                recordedQuery = RecordedVideo.RecordedVideo.query.filter_by(pending=False, published=True) \
                    .join(Channel.Channel, RecordedVideo.RecordedVideo.channelID == Channel.Channel.id) \
                    .join(Sec.User, RecordedVideo.RecordedVideo.owningUser == Sec.User.id) \
                    .with_entities(RecordedVideo.RecordedVideo.id, RecordedVideo.RecordedVideo.owningUser,
                                   RecordedVideo.RecordedVideo.views, RecordedVideo.RecordedVideo.length,
                                   RecordedVideo.RecordedVideo.thumbnailLocation,
                                   RecordedVideo.RecordedVideo.channelName,
                                   RecordedVideo.RecordedVideo.topic, RecordedVideo.RecordedVideo.videoDate,
                                   Sec.User.pictureLocation, Channel.Channel.protected,
                                   Channel.Channel.channelName.label('ChanName')) \
                    .order_by(RecordedVideo.RecordedVideo.views.desc()).limit(16)

                clipQuery = RecordedVideo.Clips.query.filter_by(published=True) \
                    .join(RecordedVideo.RecordedVideo,
                          RecordedVideo.Clips.parentVideo == RecordedVideo.RecordedVideo.id) \
                    .join(Channel.Channel, Channel.Channel.id == RecordedVideo.RecordedVideo.channelID) \
                    .join(Sec.User, Sec.User.id == Channel.Channel.owningUser) \
                    .with_entities(RecordedVideo.Clips.id, RecordedVideo.Clips.thumbnailLocation,
                                   Channel.Channel.owningUser, RecordedVideo.Clips.views, RecordedVideo.Clips.length,
                                   RecordedVideo.Clips.clipName, Channel.Channel.protected, Channel.Channel.channelName,
                                   RecordedVideo.RecordedVideo.topic, RecordedVideo.RecordedVideo.videoDate,
                                   Sec.User.pictureLocation) \
                    .order_by(RecordedVideo.Clips.views.desc()).limit(16)

        return render_template(themes.checkOverride('index.html'), streamList=activeStreams, videoList=recordedQuery, clipList=clipQuery)

@root_bp.route('/search', methods=["POST"])
def search_page():
    if 'term' in request.form:
        search = str(request.form['term'])

        topicList = topics.topics.query.filter(topics.topics.name.contains(search)).all()

        streamerList = []
        streamerList1 = Sec.User.query.filter(Sec.User.username.contains(search)).all()
        streamerList2 = Sec.User.query.filter(Sec.User.biography.contains(search)).all()
        for stream in streamerList1:
            if stream.has_role('Streamer'):
                streamerList.append(stream)
        for stream in streamerList2:
            if stream not in streamerList and stream.has_role('streamer'):
                streamerList.append(stream)

        channelList = []
        channelList1 = Channel.Channel.query.filter(Channel.Channel.channelName.contains(search)).all()
        channelList2 = Channel.Channel.query.filter(Channel.Channel.description.contains(search)).all()
        for channel in channelList1:
            channelList.append(channel)
        for channel in channelList2:
            if channel not in channelList:
                channelList.append(channel)

        videoList = []
        videoList1 = RecordedVideo.RecordedVideo.query.filter(RecordedVideo.RecordedVideo.channelName.contains(search)).filter(RecordedVideo.RecordedVideo.pending == False, RecordedVideo.RecordedVideo.published == True).all()
        videoList2 = RecordedVideo.RecordedVideo.query.filter(RecordedVideo.RecordedVideo.description.contains(search)).filter(RecordedVideo.RecordedVideo.pending == False, RecordedVideo.RecordedVideo.published == True).all()
        for video in videoList1:
            videoList.append(video)
        for video in videoList2:
            if video not in videoList:
                videoList.append(video)

        streamList = Stream.Stream.query.filter(Stream.Stream.streamName.contains(search)).all()

        clipList = []
        clipList1 = RecordedVideo.Clips.query.filter(RecordedVideo.Clips.clipName.contains(search)).filter(RecordedVideo.Clips.published == True).all()
        clipList2 = RecordedVideo.Clips.query.filter(RecordedVideo.Clips.description.contains(search)).filter(RecordedVideo.Clips.published == True).all()
        for clip in clipList1:
            clipList.append(clip)
        for clip in clipList2:
            if clip not in clipList:
                clipList.append(clip)

        return render_template(themes.checkOverride('search.html'), topicList=topicList, streamerList=streamerList, channelList=channelList, videoList=videoList, streamList=streamList, clipList=clipList)

    return redirect(url_for('root.main_page'))

@login_required
@root_bp.route('/notifications')
def notification_page():
    notificationQuery = notifications.userNotification.query.filter_by(userID=current_user.id, read=False).order_by(notifications.userNotification.timestamp.desc())
    return render_template(themes.checkOverride('notifications.html'), notificationList=notificationQuery)

@root_bp.route('/unsubscribe')
def unsubscribe_page():
    if 'email' in request.args:
        emailAddress = request.args.get("email")
        userQuery = Sec.User.query.filter_by(email=emailAddress).first()
        if userQuery is not None:
            subscriptionQuery = subscriptions.channelSubs.query.filter_by(userID=userQuery.id).all()
            for sub in subscriptionQuery:
                db.session.delete(sub)
            db.session.commit()
        return emailAddress + " has been removed from all subscriptions"

@root_bp.route('/robots.txt')
def static_from_root():
    return send_from_directory(current_app.static_folder, request.path[1:])

@root_bp.route('/auth', methods=["POST","GET"])
def auth_check():
    sysSettings = settings.settings.query.with_entities(settings.settings.protectionEnabled).first()
    if sysSettings.protectionEnabled is False:
        return 'OK'

    channelID = ""
    if 'X-Channel-ID' in request.headers:
        channelID = request.headers['X-Channel-ID']
        channelQuery = Channel.Channel.query.filter_by(channelLoc=channelID).with_entities(Channel.Channel.id, Channel.Channel.protected).first()
        if channelQuery is not None:
            if channelQuery.protected:
                if securityFunc.check_isValidChannelViewer(channelQuery.id):
                    db.session.close()
                    return 'OK'
                else:
                    db.session.close()
                    return abort(401)
            else:
                return 'OK'

    db.session.close()
    abort(400)

@root_bp.route('/playbackAuth', methods=['POST'])
def playback_auth_handler():
    stream = request.form['name']

    streamQuery = Channel.Channel.query.filter_by(channelLoc=stream).first()
    if streamQuery is not None:

        if streamQuery.protected is False:
            db.session.close()
            return 'OK'
        else:
            username = request.form['username']
            secureHash = request.form['hash']

            if streamQuery is not None:
                requestedUser = Sec.User.query.filter_by(username=username).first()
                if requestedUser is not None:
                    isValid = False
                    validHash = None
                    if requestedUser.authType == 0:
                        validHash = hashlib.sha256((requestedUser.username + streamQuery.channelLoc + requestedUser.password).encode('utf-8')).hexdigest()
                    else:
                        validHash = hashlib.sha256((requestedUser.username + streamQuery.channelLoc + requestedUser.oAuthID).encode('utf-8')).hexdigest()
                    if secureHash == validHash:
                        isValid = True
                    if isValid is True:
                        if streamQuery.owningUser == requestedUser.id:
                            db.session.close()
                            return 'OK'
                        else:
                            if securityFunc.check_isUserValidRTMPViewer(requestedUser.id,streamQuery.id):
                                db.session.close()
                                return 'OK'
    db.session.close()
    return abort(400)