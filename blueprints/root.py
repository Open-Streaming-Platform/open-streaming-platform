import hashlib

from flask import Blueprint, request, url_for, render_template, redirect, current_app, send_from_directory, abort, flash, Response
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
from classes import banList

from functions import themes
from functions import system
from functions import securityFunc
from functions import cachedDbCalls

root_bp = Blueprint('root', __name__)


@root_bp.route('/')
def main_page():

    firstRunCheck = system.check_existing_settings()

    if firstRunCheck is False:
        return render_template('/firstrun.html')

    else:
        sysSettings = cachedDbCalls.getSystemSettings()
        activeStreams = Stream.Stream.query.filter_by(active=True).order_by(Stream.Stream.currentViewers).all()

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
                               Sec.User.pictureLocation, RecordedVideo.Clips.parentVideo) \
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
                               Sec.User.pictureLocation, RecordedVideo.Clips.parentVideo) \
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
                .with_entities(RecordedVideo.Clips.id, RecordedVideo.Clips.thumbnailLocation, Channel.Channel.owningUser, RecordedVideo.Clips.views, RecordedVideo.Clips.length, RecordedVideo.Clips.clipName, Channel.Channel.protected, Channel.Channel.channelName, RecordedVideo.RecordedVideo.topic, RecordedVideo.RecordedVideo.videoDate, Sec.User.pictureLocation, RecordedVideo.Clips.parentVideo)\
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
                                   Sec.User.pictureLocation, RecordedVideo.Clips.parentVideo) \
                    .order_by(RecordedVideo.Clips.views.desc()).limit(16)

        return render_template(themes.checkOverride('index.html'), streamList=activeStreams, videoList=recordedQuery, clipList=clipQuery, panelList=themes.getPagePanels('root.main_page'))

@root_bp.route('/search', methods=["POST", "GET"])
def search_page():
    # Deprecated Method Under Old Theme - To be removed in future
    if request.method == 'POST':
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

            streamList = Stream.Stream.query.filter(Stream.Stream.active == True, Stream.Stream.streamName.contains(search)).all()

            clipList = []
            clipList1 = RecordedVideo.Clips.query.filter(RecordedVideo.Clips.clipName.contains(search)).filter(RecordedVideo.Clips.published == True).all()
            clipList2 = RecordedVideo.Clips.query.filter(RecordedVideo.Clips.description.contains(search)).filter(RecordedVideo.Clips.published == True).all()
            for clip in clipList1:
                clipList.append(clip)
            for clip in clipList2:
                if clip not in clipList:
                    clipList.append(clip)

            return render_template(themes.checkOverride('search.html'), topicList=topicList, streamerList=streamerList, channelList=channelList, videoList=videoList, streamList=streamList, clipList=clipList)

    elif request.method == 'GET':
        if 'type' in request.args and 'term' in request.args:
            type = request.args.get("type")
            term = request.args.get("term")

            if type == "channels":
                sysSettings = cachedDbCalls.getSystemSettings()

                channelList = cachedDbCalls.searchChannels(term)

                if sysSettings.showEmptyTables is False:
                    channelListArray = []
                    for channel in channelList:
                        chanVidQuery = cachedDbCalls.getChannelVideos(channel.id)
                        if len(chanVidQuery) > 0:
                            channelListArray.append(channel)
                    channelList = channelListArray
                return render_template(themes.checkOverride('videoListView.html'), userChannels=channelList)
            elif type == "streams":
                openStreams = cachedDbCalls.searchStreams(term)
                return render_template(themes.checkOverride('videoListView.html'), openStreams=openStreams)
            elif type == "videos":
                recordedVids = cachedDbCalls.searchVideos(term)
                return render_template(themes.checkOverride('videoListView.html'), recordedVids=recordedVids)
            elif type == "clips":
                clipsList = cachedDbCalls.searchClips(term)
                return render_template(themes.checkOverride('videoListView.html'), clipsList=clipsList)
            elif type == "users":
                streamerList = cachedDbCalls.searchUsers(term)
                return render_template(themes.checkOverride('streamers.html'), streamerList=streamerList)
            elif type == "all":
                sysSettings = cachedDbCalls.getSystemSettings()
                channelList = cachedDbCalls.searchChannels(term)

                if sysSettings.showEmptyTables is False:
                    channelListArray = []
                    for channel in channelList:
                        chanVidQuery = cachedDbCalls.getChannelVideos(channel.id)
                        if len(chanVidQuery) > 0:
                            channelListArray.append(channel)
                    channelList = channelListArray
                
                openStreams = cachedDbCalls.searchStreams(term)
                recordedVids = cachedDbCalls.searchVideos(term)
                clipsList = cachedDbCalls.searchClips(term)
                userList = cachedDbCalls.searchUsers(term)
                return render_template(themes.checkOverride('videoListView.html'), userChannels=channelList, openStreams=openStreams, recordedVids=recordedVids, clipsList=clipsList, userList=userList)

    return redirect(url_for('root.main_page'))

@root_bp.route('/messages')
@login_required
def messages_page():
    messageList = notifications.userMessage.query.filter_by(toUserID=current_user.id).all()
    messageBanList = banList.messageBanList.query.filter_by(userID=current_user.id).all()
    return render_template(themes.checkOverride('messages.html'), messageList=messageList, messageBanList=messageBanList)

@root_bp.route('/notifications')
@login_required
def notification_page():
    notificationQuery = notifications.userNotification.query.filter_by(userID=current_user.id, read=False).order_by(notifications.userNotification.timestamp.desc())
    return render_template(themes.checkOverride('notifications.html'), notificationList=notificationQuery)

@root_bp.route('/unsubscribe')
@login_required
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

# Serve Service Worker from Project Root
@root_bp.route('/sw.js')
def static_from_root_sw():
    return send_from_directory(current_app.static_folder, request.path[1:])

# Link to Profile Via Username
@root_bp.route('/u/<username>')
def vanityURL_username_link(username):
    userQuery = Sec.User.query.filter_by(username=username).first()
    if userQuery is not None:
        return redirect(url_for('profile.profile_view_page',username=username))
    flash("Invalid Username","error")
    return redirect(url_for('root.main_page'))

# Link to Channels Via Vanity URLs
@root_bp.route('/c/<vanityURL>')
def vanityURL_channel_link(vanityURL):
    channelQuery = Channel.Channel.query.filter_by(vanityURL=vanityURL).first()
    if channelQuery is not None:
        return redirect(url_for('channel.channel_view_page',chanID=channelQuery.id))
    flash('Invalid Link URL','error')
    return redirect(url_for('root.main_page'))

# Link to a Channel's Live Page Via Vanity URLs
@root_bp.route('/c/<vanityURL>/live')
def vanityURL_live_link(vanityURL):
    channelQuery = Channel.Channel.query.filter_by(vanityURL=vanityURL).first()
    if channelQuery is not None:
        return redirect(url_for('liveview.view_page',loc=channelQuery.channelLoc))
    flash('Invalid Link URL','error')
    return redirect(url_for('root.main_page'))

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

@root_bp.route('/rtmpCheck', methods=["POST","GET"])
def rtmp_check():
    channelID = ""
    if 'X-Channel-ID' in request.headers:
        channelID = request.headers['X-Channel-ID']
        channelQuery = Channel.Channel.query.filter_by(channelLoc=channelID).first()
        if channelQuery is not None:
            streamList = channelQuery.stream
            if streamList != []:
                streamEntry = streamList[0]
                if streamEntry.rtmpServer is not None:
                    rtmpServerID = streamEntry.rtmpServer
                    rtmpServer = settings.rtmpServer.query.filter_by(id=rtmpServerID).first()
                    resp = Response("OK")
                    resp.headers['X_UpstreamHost'] = rtmpServer.address
                    return resp
                return abort(404)
            return abort(404)
        return abort(404)
    return abort(404)

# Redirect Streams
@root_bp.route('/proxy/<channelLoc>/<file>')
def proxy_redirect(channelLoc, file):
    sysSettings = cachedDbCalls.getSystemSettings()
    proxyAddress = sysSettings.proxyFQDN
    protocol = sysSettings.siteProtocol
    validationToken = "NA"
    user = "Guest"
    if current_user.is_authenticated:
        user = current_user.username
        if current_user.authType == 0:
            validationToken = hashlib.sha256(
                (current_user.username + channelLoc + current_user.password).encode('utf-8')).hexdigest()
        else:
            validationToken = hashlib.sha256(
                (current_user.username + channelLoc + current_user.oAuthID).encode('utf-8')).hexdigest()

    redirectURL = protocol + proxyAddress + '/live/' + channelLoc + '/' + file
    resp = redirect(redirectURL)
    proxyAuthToken = user + "_" + validationToken
    resp.set_cookie('proxyAuth', proxyAuthToken, domain=proxyAddress)
    return resp

    #return redirect(protocol + proxyAddress + '/live/' + channelLoc + '/' + file + '?user=' + user + '&token=' + validationToken)

@root_bp.route('/proxy-adapt/<channelLoc>.m3u8')
def proxy_adaptive_redirect(channelLoc):
    sysSettings = cachedDbCalls.getSystemSettings()
    proxyAddress = sysSettings.proxyFQDN
    protocol = sysSettings.siteProtocol
    return redirect(protocol + proxyAddress + '/live-adapt/' + channelLoc + '.m3u8')

@root_bp.route('/proxy-adapt/<channelLoc>/<file>')
def proxy_adaptive_subfolder_redirect(channelLoc, file):
    sysSettings = cachedDbCalls.getSystemSettings()
    proxyAddress = sysSettings.proxyFQDN
    protocol = sysSettings.siteProtocol
    return redirect(protocol + proxyAddress + '/live-adapt/' + channelLoc + '/' + file)
