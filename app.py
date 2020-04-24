# -*- coding: UTF-8 -*-
from gevent import monkey
monkey.patch_all(thread=True)

# Import Standary Python Libraries
import uuid
import socket
import shutil
import os
import subprocess
import time
import sys
import random
import json
import hashlib
import logging
import datetime

# Import 3rd Party Libraries
from flask import Flask, redirect, request, abort, render_template, url_for, flash, send_from_directory, Response, session
from flask_session import Session
from flask_security import Security, SQLAlchemyUserDatastore, login_required, current_user, roles_required
from flask_security.signals import user_registered
from sqlalchemy.sql.expression import func
from flask_socketio import emit, join_room, leave_room
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class
from flask_migrate import Migrate, migrate, upgrade
from flaskext.markdown import Markdown
from flask_debugtoolbar import DebugToolbarExtension
from flask_cors import CORS
import xmltodict
from werkzeug.middleware.proxy_fix import ProxyFix

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
from apscheduler.schedulers.background import BackgroundScheduler
import psutil
import requests

# Import Paths
cwp = sys.path[0]
sys.path.append(cwp)
sys.path.append('./classes')

#----------------------------------------------------------------------------#
# Configuration Imports
#----------------------------------------------------------------------------#
from conf import config

#----------------------------------------------------------------------------#
# Global Vars Imports
#----------------------------------------------------------------------------#
from globals import globalvars

#----------------------------------------------------------------------------#
# App Configuration Setup
#----------------------------------------------------------------------------#
coreNginxRTMPAddress = "127.0.0.1"

sysSettings = None

app = Flask(__name__)

# Flask App Environment Setup
app.debug = config.debugMode
app.wsgi_app = ProxyFix(app.wsgi_app)
app.jinja_env.cache = {}
app.config['WEB_ROOT'] = globalvars.videoRoot
app.config['SQLALCHEMY_DATABASE_URI'] = config.dbLocation
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
if config.dbLocation[:6] != "sqlite":
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = -1
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 600
    app.config['SQLALCHEMY_POOL_TIMEOUT'] = 1200
    app.config['MYSQL_DATABASE_CHARSET'] = "utf8"
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'encoding': 'utf8', 'pool_use_lifo': 'True', 'pool_size': 20, "pool_pre_ping": True}
else:
    pass
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_COOKIE_NAME'] = 'ospSession'
app.config['SECRET_KEY'] = config.secretKey
app.config['SECURITY_PASSWORD_HASH'] = "pbkdf2_sha512"
app.config['SECURITY_PASSWORD_SALT'] = config.passwordSalt
app.config['SECURITY_REGISTERABLE'] = config.allowRegistration
app.config['SECURITY_RECOVERABLE'] = True
app.config['SECURITY_CONFIRMABLE'] = config.requireEmailRegistration
app.config['SECURITY_SEND_REGISTER_EMAIL'] = config.requireEmailRegistration
app.config['SECURITY_CHANGABLE'] = True
app.config['SECURITY_USER_IDENTITY_ATTRIBUTES'] = ['username','email']
app.config['SECURITY_FLASH_MESSAGES'] = True
app.config['UPLOADED_PHOTOS_DEST'] = app.config['WEB_ROOT'] + 'images'
app.config['UPLOADED_DEFAULT_DEST'] = app.config['WEB_ROOT'] + 'images'
app.config['SECURITY_POST_LOGIN_VIEW'] = 'main_page'
app.config['SECURITY_POST_LOGOUT_VIEW'] = 'main_page'
app.config['SECURITY_MSG_EMAIL_ALREADY_ASSOCIATED'] = ("Username or Email Already Associated with an Account", "error")
app.config['SECURITY_MSG_INVALID_PASSWORD'] = ("Invalid Username or Password", "error")
app.config['SECURITY_MSG_INVALID_EMAIL_ADDRESS'] = ("Invalid Username or Password","error")
app.config['SECURITY_MSG_USER_DOES_NOT_EXIST'] = ("Invalid Username or Password","error")
app.config['SECURITY_MSG_DISABLED_ACCOUNT'] = ("Account Disabled","error")
app.config['VIDEO_UPLOAD_TEMPFOLDER'] = app.config['WEB_ROOT'] + 'videos/temp'
app.config["VIDEO_UPLOAD_EXTENSIONS"] = ["PNG", "MP4"]

logger = logging.getLogger('gunicorn.error').handlers

#----------------------------------------------------------------------------#
# Modal Imports
#----------------------------------------------------------------------------#

from classes import Stream
from classes import Channel
from classes import dbVersion
from classes import RecordedVideo
from classes import topics
from classes import settings
from classes import banList
from classes import Sec
from classes import upvotes
from classes import apikey
from classes import views
from classes import comments
from classes import invites
from classes import webhook
from classes import logs
from classes import subscriptions
from classes import notifications

#----------------------------------------------------------------------------#
# Function Imports
#----------------------------------------------------------------------------#
from functions import database
from functions import system
from functions import securityFunc
from functions import cache
from functions import themes
from functions import votes
from functions import videoFunc
from functions import webhookFunc
from functions import commentsFunc
from functions import subsFunc

#----------------------------------------------------------------------------#
# Begin App Initialization
#----------------------------------------------------------------------------#
# Initialize Flask-Limiter
if config.redisPassword == '' or config.redisPassword is None:
    app.config["RATELIMIT_STORAGE_URL"] = "redis://" + config.redisHost + ":" + str(config.redisPort)
else:
    app.config["RATELIMIT_STORAGE_URL"] = "redis://" + config.redisPassword + "@" + config.redisHost + ":" + str(config.redisPort)
from classes.shared import limiter
limiter.init_app(app)

# Initialize Redis for Flask-Session
if config.redisPassword != '':
    r = redis.Redis(host=config.redisHost, port=config.redisPort)
    app.config["SESSION_REDIS"] = r
else:
    r = redis.Redis(host=config.redisHost, port=config.redisPort, password=config.redisPassword)
    app.config["SESSION_REDIS"] = r
r.flushdb()

# Initialize Flask-SocketIO
from classes.shared import socketio
if config.redisPassword != '':
    socketio.init_app(app, logger=False, engineio_logger=False, message_queue="redis://" + config.redisHost + ":" + str(config.redisPort),  cors_allowed_origins=[])
else:
    socketio.init_app(app, logger=False, engineio_logger=False, message_queue="redis://" + config.redisPassword + "@" + config.redisHost + ":" + str(config.redisPort),  cors_allowed_origins=[])

# Begin Database Initialization
from classes.shared import db
db.init_app(app)
db.app = app
migrateObj = Migrate(app, db)

# Initialize Flask-Session
Session(app)

# Initialize Flask-CORS Config
cors = CORS(app, resources={r"/apiv1/*": {"origins": "*"}})

# Initialize Debug Toolbar
toolbar = DebugToolbarExtension(app)

# Initialize Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, Sec.User, Sec.Role)
security = Security(app, user_datastore, register_form=Sec.ExtendedRegisterForm, confirm_register_form=Sec.ExtendedConfirmRegisterForm, login_form=Sec.OSPLoginForm)

# Initialize Flask-Uploads
photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)
patch_request_class(app)

# Initialize Flask-Markdown
md = Markdown(app, extensions=['tables'])

# Initialize Scheduler
scheduler = BackgroundScheduler()
#scheduler.add_job(func=processAllHubConnections, trigger="interval", seconds=180)
scheduler.start()

# Attempt Database Load and Validation
try:
    database.init(app, user_datastore)
except:
    print("DB Load Fail due to Upgrade or Issues")

# Initialize Flask-Mail
from classes.shared import email

email.init_app(app)
email.app = app

#----------------------------------------------------------------------------#
# SocketIO Handler Import
#----------------------------------------------------------------------------#
from functions.socketio import connections
from functions.socketio import video
from functions.socketio import stream
from functions.socketio import chat
from functions.socketio import vote
from functions.socketio import invites
from functions.socketio import webhooks
from functions.socketio import edge
from functions.socketio import subscription
from functions.socketio import thumbnail
from functions.socketio import syst

#----------------------------------------------------------------------------#
# Blueprint Filter Imports
#----------------------------------------------------------------------------#
from blueprints.apiv1 import api_v1
from blueprints.streamers import streamers_bp
from blueprints.channels import channels_bp
from blueprints.topics import topics_bp
from blueprints.play import play_bp
from blueprints.clip import clip_bp
from blueprints.upload import upload_bp
from blueprints.settings import settings_bp

# Register all Blueprints
app.register_blueprint(api_v1)
app.register_blueprint(channels_bp)
app.register_blueprint(play_bp)
app.register_blueprint(clip_bp)
app.register_blueprint(streamers_bp)
app.register_blueprint(topics_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(settings_bp)

#----------------------------------------------------------------------------#
# Template Filter Imports
#----------------------------------------------------------------------------#
from functions import templateFilters

# Initialize Jinja2 Template Filters
templateFilters.init(app)

# Log Successful Start and Transfer Control
system.newLog("0", "OSP Started Up Successfully - version: " + str(globalvars.version))

#----------------------------------------------------------------------------#
# Jinja 2 Gloabl Environment Functions
#----------------------------------------------------------------------------#
app.jinja_env.globals.update(check_isValidChannelViewer=securityFunc.check_isValidChannelViewer)
app.jinja_env.globals.update(check_isCommentUpvoted=votes.check_isCommentUpvoted)

#----------------------------------------------------------------------------#
# Context Processors
#----------------------------------------------------------------------------#

@app.context_processor
def inject_notifications():
    notificationList = []
    if current_user.is_authenticated:
        userNotificationQuery = notifications.userNotification.query.filter_by(userID=current_user.id).all()
        for entry in userNotificationQuery:
            if entry.read is False:
                notificationList.append(entry)
        notificationList.sort(key=lambda x: x.timestamp, reverse=True)
    return dict(notifications=notificationList)


@app.context_processor
def inject_sysSettings():

    sysSettings = db.session.query(settings.settings).first()
    allowRegistration = config.allowRegistration

    return dict(sysSettings=sysSettings, allowRegistration=allowRegistration)

@app.context_processor
def inject_ownedChannels():
    if current_user.is_authenticated:
        if current_user.has_role("Streamer"):
            ownedChannels = Channel.Channel.query.filter_by(owningUser=current_user.id).with_entities(Channel.Channel.id, Channel.Channel.channelLoc, Channel.Channel.channelName).all()

            return dict(ownedChannels=ownedChannels)
        else:
            return dict(ownedChannels=[])
    else:
        return dict(ownedChannels=[])

#----------------------------------------------------------------------------#
# Flask Signal Handlers.
#----------------------------------------------------------------------------#
@user_registered.connect_via(app)
def user_registered_sighandler(app, user, confirm_token):
    default_role = user_datastore.find_role("User")
    user_datastore.add_role_to_user(user, default_role)
    webhookFunc.runWebhook("ZZZ", 20, user=user.username)
    system.newLog(1, "A New User has Registered - Username:" + str(user.username))
    if config.requireEmailRegistration:
        flash("An email has been sent to the email provided. Please check your email and verify your account to activate.")
    db.session.commit()

#----------------------------------------------------------------------------#
# Error Handlers.
#----------------------------------------------------------------------------#
@app.errorhandler(404)
def page_not_found(e):
    sysSettings = settings.settings.query.first()
    system.newLog(0, "404 Error - " + str(request.url))
    return render_template(themes.checkOverride('404.html'), sysSetting=sysSettings), 404

@app.errorhandler(500)
def page_not_found(e):
    sysSettings = settings.settings.query.first()
    system.newLog(0,"500 Error - " + str(request.url))
    return render_template(themes.checkOverride('500.html'), sysSetting=sysSettings, error=e), 500

#----------------------------------------------------------------------------#
# Additional Handlers.
#----------------------------------------------------------------------------#
@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

#----------------------------------------------------------------------------#
# Route Controllers.
#----------------------------------------------------------------------------#
@app.route('/')
def main_page():

    firstRunCheck = system.check_existing_settings()

    if firstRunCheck is False:
        return render_template('/firstrun.html')

    else:
        activeStreams = Stream.Stream.query.order_by(Stream.Stream.currentViewers).all()

        randomRecorded = RecordedVideo.RecordedVideo.query.filter_by(pending=False, published=True)\
            .join(Channel.Channel, RecordedVideo.RecordedVideo.channelID == Channel.Channel.id)\
            .join(Sec.User, RecordedVideo.RecordedVideo.owningUser == Sec.User.id)\
            .with_entities(RecordedVideo.RecordedVideo.id, RecordedVideo.RecordedVideo.owningUser, RecordedVideo.RecordedVideo.views, RecordedVideo.RecordedVideo.length, RecordedVideo.RecordedVideo.thumbnailLocation, RecordedVideo.RecordedVideo.channelName, RecordedVideo.RecordedVideo.topic, RecordedVideo.RecordedVideo.videoDate, Sec.User.pictureLocation, Channel.Channel.protected, Channel.Channel.channelName.label('ChanName'))\
            .order_by(func.random()).limit(16)

        randomClips = RecordedVideo.Clips.query.filter_by(published=True)\
            .join(RecordedVideo.RecordedVideo, RecordedVideo.Clips.parentVideo == RecordedVideo.RecordedVideo.id)\
            .join(Channel.Channel, Channel.Channel.id==RecordedVideo.RecordedVideo.channelID)\
            .join(Sec.User, Sec.User.id == Channel.Channel.owningUser)\
            .with_entities(RecordedVideo.Clips.id, RecordedVideo.Clips.thumbnailLocation, Channel.Channel.owningUser, RecordedVideo.Clips.views, RecordedVideo.Clips.length, RecordedVideo.Clips.clipName, Channel.Channel.protected, Channel.Channel.channelName, RecordedVideo.RecordedVideo.topic, RecordedVideo.RecordedVideo.videoDate, Sec.User.pictureLocation)\
            .order_by(func.random()).limit(16)

        return render_template(themes.checkOverride('index.html'), streamList=activeStreams, randomRecorded=randomRecorded, randomClips=randomClips)

@app.route('/view/<loc>/')
def view_page(loc):
    sysSettings = settings.settings.query.first()

    requestedChannel = Channel.Channel.query.filter_by(channelLoc=loc).first()

    if requestedChannel is not None:

        if requestedChannel.protected and sysSettings.protectionEnabled:
            if not securityFunc.check_isValidChannelViewer(requestedChannel.id):
                return render_template(themes.checkOverride('channelProtectionAuth.html'))

        streamData = Stream.Stream.query.filter_by(streamKey=requestedChannel.streamKey).first()

        streamURL = ''
        edgeQuery = settings.edgeStreamer.query.filter_by(active=True).all()
        if edgeQuery == []:
            if sysSettings.adaptiveStreaming is True:
                streamURL = '/live-adapt/' + requestedChannel.channelLoc + '.m3u8'
            elif requestedChannel.record is True and requestedChannel.owner.has_role("Recorder") and sysSettings.allowRecording is True:
                streamURL = '/live-rec/' + requestedChannel.channelLoc + '/index.m3u8'
            elif requestedChannel.record is False or requestedChannel.owner.has_role("Recorder") is False or sysSettings.allowRecording is False :
                streamURL = '/live/' + requestedChannel.channelLoc + '/index.m3u8'
        else:
            # Handle Selecting the Node using Round Robin Logic
            if sysSettings.adaptiveStreaming is True:
                streamURL = '/edge-adapt/' + requestedChannel.channelLoc + '.m3u8'
            else:
                streamURL = '/edge/' + requestedChannel.channelLoc + '/index.m3u8'

        requestedChannel.views = requestedChannel.views + 1
        if streamData is not None:
            streamData.totalViewers = streamData.totalViewers + 1
        db.session.commit()

        topicList = topics.topics.query.all()

        chatOnly = request.args.get("chatOnly")

        if chatOnly == "True" or chatOnly == "true":
            if requestedChannel.chatEnabled:
                hideBar = False

                hideBarReq = request.args.get("hideBar")
                if hideBarReq == "True" or hideBarReq == "true":
                    hideBar = True

                return render_template(themes.checkOverride('chatpopout.html'), stream=streamData, streamURL=streamURL, sysSettings=sysSettings, channel=requestedChannel, hideBar=hideBar)
            else:
                flash("Chat is Not Enabled For This Stream","error")

        isEmbedded = request.args.get("embedded")

        newView = views.views(0, requestedChannel.id)
        db.session.add(newView)
        db.session.commit()

        requestedChannel = Channel.Channel.query.filter_by(channelLoc=loc).first()

        if isEmbedded is None or isEmbedded == "False":

            secureHash = None
            rtmpURI = None

            endpoint = 'live'

            if requestedChannel.protected:
                if current_user.is_authenticated:
                    secureHash = hashlib.sha256((current_user.username + requestedChannel.channelLoc + current_user.password).encode('utf-8')).hexdigest()
                    username = current_user.username
                    rtmpURI = 'rtmp://' + sysSettings.siteAddress + ":1935/" + endpoint + "/" + requestedChannel.channelLoc + "?username=" + username + "&hash=" + secureHash
            else:
                rtmpURI = 'rtmp://' + sysSettings.siteAddress + ":1935/" + endpoint + "/" + requestedChannel.channelLoc

            randomRecorded = RecordedVideo.RecordedVideo.query.filter_by(pending=False, published=True, channelID=requestedChannel.id).order_by(func.random()).limit(16)

            clipsList = []
            for vid in requestedChannel.recordedVideo:
                for clip in vid.clips:
                    if clip.published is True:
                        clipsList.append(clip)
            clipsList.sort(key=lambda x: x.views, reverse=True)

            subState = False
            if current_user.is_authenticated:
                chanSubQuery = subscriptions.channelSubs.query.filter_by(channelID=requestedChannel.id, userID=current_user.id).first()
                if chanSubQuery is not None:
                    subState = True

            return render_template(themes.checkOverride('channelplayer.html'), stream=streamData, streamURL=streamURL, topics=topicList, randomRecorded=randomRecorded, channel=requestedChannel, clipsList=clipsList,
                                   subState=subState, secureHash=secureHash, rtmpURI=rtmpURI)
        else:
            isAutoPlay = request.args.get("autoplay")
            if isAutoPlay is None:
                isAutoPlay = False
            elif isAutoPlay.lower() == 'true':
                isAutoPlay = True
            else:
                isAutoPlay = False
            return render_template(themes.checkOverride('player_embed.html'), channel=requestedChannel, stream=streamData, streamURL=streamURL, topics=topicList, isAutoPlay=isAutoPlay)

    else:
        flash("No Live Stream at URL","error")
        return redirect(url_for("main_page"))

@app.route('/unsubscribe')
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

@app.route('/rtmpstat/<node>')
@login_required
@roles_required('Admin')
def rtmpStat_page(node):
    r = None
    if node == "localhost":
        r = requests.get("http://127.0.0.1:9000/stat").text
    else:
        nodeQuery = settings.edgeStreamer.query.filter_by(address=node).first()
        if nodeQuery is not None:
            r = requests.get('http://' + nodeQuery.address + ":9000/stat").text

    if r is not None:
        data = None
        try:
            data = xmltodict.parse(r)
            data = json.dumps(data)
        except:
            return abort(500)
        return (data)
    return abort(500)

@app.route('/search', methods=["POST"])
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

    return redirect(url_for('main_page'))

@login_required
@app.route('/notifications')
def notification_page():
    notificationQuery = notifications.userNotification.query.filter_by(userID=current_user.id, read=False).order_by(notifications.userNotification.timestamp.desc())
    return render_template(themes.checkOverride('notifications.html'), notificationList=notificationQuery)

@app.route('/auth', methods=["POST","GET"])
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

### Start NGINX-RTMP Authentication Functions

@app.route('/auth-key', methods=['POST'])
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

                validAddress = system.formatSiteAddress(sysSettings.siteAddress)

                externalIP = socket.gethostbyname(validAddress)
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

                if channelRequest.record is False or sysSettings.allowRecording is False or userQuery.has_role("Recorder") is False:
                    if sysSettings.adaptiveStreaming:
                        return redirect('rtmp://' + coreNginxRTMPAddress + '/stream-data-adapt/' + channelRequest.channelLoc, code=302)
                    else:
                        return redirect('rtmp://' + coreNginxRTMPAddress + '/stream-data/' + channelRequest.channelLoc, code=302)
                elif channelRequest.record is True and sysSettings.allowRecording is True and userQuery.has_role("Recorder"):

                    userCheck = Sec.User.query.filter_by(id=channelRequest.owningUser).first()
                    existingRecordingQuery = RecordedVideo.RecordedVideo.query.filter_by(channelID=channelRequest.id, pending=True).all()
                    if existingRecordingQuery:
                        for recording in existingRecordingQuery:
                            db.session.delete(recording)
                            db.session.commit()

                    newRecording = RecordedVideo.RecordedVideo(userCheck.id, channelRequest.id, channelRequest.channelName, channelRequest.topic, 0, "", currentTime, channelRequest.allowComments, False)
                    db.session.add(newRecording)
                    db.session.commit()
                    if sysSettings.adaptiveStreaming:
                        return redirect('rtmp://' + coreNginxRTMPAddress + '/streamrec-data-adapt/' + channelRequest.channelLoc, code=302)
                    else:
                        return redirect('rtmp://' + coreNginxRTMPAddress + '/streamrec-data/' + channelRequest.channelLoc, code=302)
                else:
                    returnMessage = {'time': str(currentTime), 'status': 'Streaming Error due to mismatched settings', 'key': str(key), 'ipAddress': str(ipaddress)}
                    print(returnMessage)
                    db.session.close()
                    return abort(400)
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


@app.route('/auth-user', methods=['POST'])
def user_auth_check():
    sysSettings = settings.settings.query.first()

    key = request.form['name']
    ipaddress = request.form['addr']

    requestedChannel = Channel.Channel.query.filter_by(channelLoc=key).first()

    if requestedChannel is not None:
        authedStream = Stream.Stream.query.filter_by(streamKey=requestedChannel.streamKey).first()

        if authedStream is not None:
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

            inputLocation = ""
            if requestedChannel.protected and sysSettings.protectionEnabled:
                owningUser = Sec.User.query.filter_by(id=requestedChannel.owningUser).first()
                secureHash = hashlib.sha256((owningUser.username + requestedChannel.channelLoc + owningUser.password).encode('utf-8')).hexdigest()
                username = owningUser.username
                inputLocation = 'rtmp://' + coreNginxRTMPAddress + ":1935/live/" + requestedChannel.channelLoc + "?username=" + username + "&hash=" + secureHash
            else:
                inputLocation = "rtmp://" + coreNginxRTMPAddress + ":1935/live/" + requestedChannel.channelLoc

            # Begin RTMP Restream Function
            if requestedChannel.rtmpRestream is True:

                p = subprocess.Popen(["ffmpeg", "-i", inputLocation, "-c", "copy", "-f", "flv", requestedChannel.rtmpRestreamDestination, "-c:v", "libx264", "-maxrate", str(sysSettings.restreamMaxBitrate) + "k", "-bufsize", "6000k", "-c:a", "aac", "-b:a", "160k", "-ac", "2"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                globalvars.restreamSubprocesses[requestedChannel.channelLoc] = p

            # Start OSP Edge Nodes
            ospEdgeNodeQuery = settings.edgeStreamer.query.filter_by(active=True).all()
            if ospEdgeNodeQuery is not []:
                globalvars.edgeRestreamSubprocesses[requestedChannel.channelLoc] = []

                for node in ospEdgeNodeQuery:
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


@app.route('/deauth-user', methods=['POST'])
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
            if channelRequest.rtmpRestream is True:
                if channelRequest.channelLoc in globalvars.restreamSubprocesses:
                    p = globalvars.restreamSubprocesses[channelRequest.channelLoc]
                    p.kill()
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


@app.route('/recComplete', methods=['POST'])
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

    videos_root = app.config['WEB_ROOT'] + 'videos/'
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

@app.route('/playbackAuth', methods=['POST'])
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
                    validHash = hashlib.sha256((requestedUser.username + streamQuery.channelLoc + requestedUser.password).encode('utf-8')).hexdigest()
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

@app.route('/robots.txt')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])

if __name__ == '__main__':
    app.jinja_env.auto_reload = False
    app.config['TEMPLATES_AUTO_RELOAD'] = False
    socketio.run(app, Debug=config.debugMode)
