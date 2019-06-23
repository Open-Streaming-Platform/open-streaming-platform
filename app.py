# -*- coding: UTF-8 -*-

import git

from flask import Flask, redirect, request, abort, render_template, url_for, flash, send_from_directory, make_response
from flask_security import Security, SQLAlchemyUserDatastore, login_required, current_user, roles_required
from flask_security.utils import hash_password
from flask_security.signals import user_registered
from flask_security import utils
from sqlalchemy.sql.expression import func
from sqlalchemy import desc, asc
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class
from flask_mail import Mail
from flask_migrate import Migrate, migrate, upgrade
from apiv1 import api_v1

import uuid

import psutil

import socket

import shutil
import os
import subprocess
import time
import sys
import random
import ipaddress
import requests
from threading import Thread
from functools import wraps
import json

#Import Paths
cwp = sys.path[0]
sys.path.append(cwp)
sys.path.append('./classes')


from html.parser import HTMLParser

import logging

import datetime

from conf import config

version = "beta-2"

app = Flask(__name__)

from werkzeug.contrib.fixers import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app)
app.jinja_env.cache = {}

app.config['SQLALCHEMY_DATABASE_URI'] = config.dbLocation
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
if config.dbLocation[:6] != "sqlite":
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = -1
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 1600
    app.config['MYSQL_DATABASE_CHARSET'] = "utf8"
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'encoding': 'utf8', 'pool_use_lifo': 'True', 'pool_size': 20}
else:
    pass

app.config['SECRET_KEY'] = config.secretKey
app.config['SECURITY_PASSWORD_HASH'] = "pbkdf2_sha512"
app.config['SECURITY_PASSWORD_SALT'] = config.passwordSalt
app.config['SECURITY_REGISTERABLE'] = True
app.config['SECURITY_RECOVERABLE'] = True
app.config['SECURITY_CHANGABLE'] = True
app.config['SECURITY_USER_IDENTITY_ATTRIBUTES'] = ['username','email']
app.config['SECURITY_FLASH_MESSAGES'] = True
app.config['UPLOADED_PHOTOS_DEST'] = '/var/www/images'
app.config['UPLOADED_DEFAULT_DEST'] = '/var/www/images'
app.config['SECURITY_POST_LOGIN_VIEW'] = 'main_page'
app.config['SECURITY_POST_LOGOUT_VIEW'] = 'main_page'

app.config['SECURITY_MSG_EMAIL_ALREADY_ASSOCIATED'] = ("Username or Email Already Associated with an Account", "error")
app.config['SECURITY_MSG_INVALID_PASSWORD'] = ("Invalid Username or Password", "error")
app.config['SECURITY_MSG_INVALID_EMAIL_ADDRESS'] = ("Invalid Username or Password","error")
app.config['SECURITY_MSG_USER_DOES_NOT_EXIST'] = ("Invalid Username or Password","error")
app.config['SECURITY_MSG_DISABLED_ACCOUNT'] = ("Account Disabled","error")

logger = logging.getLogger('gunicorn.error').handlers

#socketio = SocketIO(app,logger=True)

appDBVersion = 0.45

from classes.shared import db
from classes.shared import socketio

socketio.init_app(app)

db.init_app(app)
db.app = app
migrateObj = Migrate(app, db)

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

sysSettings = None

app.register_blueprint(api_v1)

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, Sec.User, Sec.Role)
security = Security(app, user_datastore, register_form=Sec.ExtendedRegisterForm, confirm_register_form=Sec.ExtendedConfirmRegisterForm)

# Setup Flask-Uploads
photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)
patch_request_class(app)

# Establish Channel User List
streamUserList = {}


def init_db_values():
    db.create_all()

    # Logic to Check the DB Version
    dbVersionQuery = dbVersion.dbVersion.query.first()

    if dbVersionQuery == None:
        newDBVersion = dbVersion.dbVersion(appDBVersion)
        db.session.add(newDBVersion)
        db.session.commit()
        with app.app_context():
            migrate_db = migrate()
            print(migrate_db)
            upgrade_db = upgrade()
            print(upgrade_db)

    elif dbVersionQuery.version != appDBVersion:
        dbVersionQuery.version = appDBVersion
        db.session.commit()
        pass

    # Setup Default User Roles
    user_datastore.find_or_create_role(name='Admin', description='Administrator')
    user_datastore.find_or_create_role(name='User', description='User')
    user_datastore.find_or_create_role(name='Streamer', description='Streamer')

    topicList = [("Other","None")]
    for topic in topicList:
        existingTopic = topics.topics.query.filter_by(name=topic[0]).first()
        if existingTopic is None:
            newTopic = topics.topics(topic[0], topic[1])
            db.session.add(newTopic)
    db.session.commit()

    sysSettings = settings.settings.query.first()

    if sysSettings.version != version:
        sysSettings.version = version
        db.session.commit()

    if sysSettings != None:
        # Sets the Default Theme is None is Set - Usual Cause is Moving from Alpha to Beta
        if sysSettings.systemTheme == None:
            sysSettings.systemTheme = "Default"
            db.session.commit()
        if sysSettings.version == "None":
            sysSettings.version = version
            db.session.commit()
        # Sets Registration to Required if None is Set - Change from Beta 1 to Beta 2
        if sysSettings.requireConfirmedEmail == None:
            sysSettings.requireConfirmedEmail = True
            db.session.commit()
        # Sets allowComments to False if None is Set - Usual Cause is moving from Alpha to Beta
        if sysSettings.allowComments == None:
            sysSettings.allowComments = False
            db.session.commit()
        # Checks Channel Settings and Corrects Missing Fields - Usual Cause is moving from Alpha to Beta
        channelQuery = Channel.Channel.query.filter_by(chatBG=None).all()
        for chan in channelQuery:
            chan.chatBG = "Standard"
            chan.chatTextColor = "#FFFFFF"
            chan.chatAnimation = "slide-in-left"
            db.session.commit()
        channelQuery = Channel.Channel.query.filter_by(channelMuted=None).all()
        for chan in channelQuery:
            chan.channelMuted = False
            db.session.commit()
        channelQuery = Channel.Channel.query.filter_by(currentViewers=None).all()
        for chan in channelQuery:
            chan.currentViewers = 0
            db.session.commit()

        sysSettings = settings.settings.query.first()

        app.config['SERVER_NAME'] = None
        app.config['SECURITY_EMAIL_SENDER'] = sysSettings.smtpSendAs
        app.config['MAIL_SERVER'] = sysSettings.smtpAddress
        app.config['MAIL_PORT'] = sysSettings.smtpPort
        app.config['MAIL_USE_SSL'] = sysSettings.smtpSSL
        app.config['MAIL_USE_TLS'] = sysSettings.smtpTLS
        app.config['MAIL_USERNAME'] = sysSettings.smtpUsername
        app.config['MAIL_PASSWORD'] = sysSettings.smtpPassword
        app.config['SECURITY_CONFIRMABLE'] = sysSettings.requireConfirmedEmail
        app.config['SECURITY_SEND_REGISTER_EMAIL'] = sysSettings.requireConfirmedEmail
        app.config['SECURITY_FORGOT_PASSWORD_TEMPLATE'] = 'themes/' + sysSettings.systemTheme + '/security/forgot_password.html'
        app.config['SECURITY_LOGIN_USER_TEMPLATE'] = 'themes/' + sysSettings.systemTheme + '/security/login_user.html'
        app.config['SECURITY_REGISTER_USER_TEMPLATE'] = 'themes/' + sysSettings.systemTheme + '/security/register_user.html'
        app.config['SECURITY_SEND_CONFIRMATION_TEMPLATE'] = 'themes/'  + sysSettings.systemTheme + '/security/send_confirmation.html'
        app.config['SECURITY_RESET_PASSWORD_TEMPLATE'] = 'themes/' + sysSettings.systemTheme + '/security/reset_password.html'
        app.config['SECURITY_EMAIL_SUBJECT_PASSWORD_RESET'] = sysSettings.siteName + " - Password Reset Request"
        app.config['SECURITY_EMAIL_SUBJECT_REGISTER'] = sysSettings.siteName + " - Welcome!"
        app.config['SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE'] = sysSettings.siteName + " - Password Reset Notification"
        app.config['SECURITY_EMAIL_SUBJECT_CONFIRM'] = sysSettings.siteName + " - Email Confirmation Request"

        app.config.update(SECURITY_REGISTERABLE=sysSettings.allowRegistration)

        ## Begin DB UTF8MB4 Fixes To Convert The DB if Needed
        if config.dbLocation[:6] != "sqlite":
            dbEngine = db.engine
            dbConnection = dbEngine.connect()
            dbConnection.execute("ALTER DATABASE `%s` CHARACTER SET 'utf8' COLLATE 'utf8_unicode_ci'" % dbEngine.url.database)

            sql = "SELECT DISTINCT(table_name) FROM information_schema.columns WHERE table_schema = '%s'" % dbEngine.url.database

            results = dbConnection.execute(sql)
            for row in results:
                sql = "ALTER TABLE `%s` convert to character set DEFAULT COLLATE DEFAULT" % (row[0])
                db.Connection.execute(sql)
            db.close()
        ## End DB UT8MB4 Fixes

def check_existing_users():
    existingUserQuery = Sec.User.query.all()

    if existingUserQuery == []:
        return False
    else:
        return True


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_html(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def asynch(func):

    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target = func, args = args, kwargs = kwargs)
        func_hl.start()
        return func_hl

    return async_func

def formatSiteAddress(systemAddress):
    try:
        ipaddress.ip_address(systemAddress)
        return systemAddress
    except ValueError:
        try:
            ipaddress.ip_address(systemAddress.split(':')[0])
            return systemAddress.split(':')[0]
        except ValueError:
            return systemAddress

def getVidLength(input_video):
    result = subprocess.check_output(['ffprobe', '-i', input_video, '-show_entries', 'format=duration', '-v', 'quiet', '-of', 'csv=%s' % ("p=0")])
    return float(result)

def get_Video_Upvotes(videoID):
    videoUpVotesQuery = upvotes.videoUpvotes.query.filter_by(videoID=videoID).count()
    result = videoUpVotesQuery
    return result

def get_Stream_Upvotes(videoID):
    videoUpVotesQuery = upvotes.streamUpvotes.query.filter_by(streamID=videoID).count()
    result = videoUpVotesQuery
    return result

def check_isValidChannelViewer(channelID):
    if current_user.is_authenticated:
        channelQuery = Channel.Channel.query.filter_by(id=channelID).first()
        if channelQuery.owningUser is current_user.id:
            return True
        else:
            inviteQuery = invites.invitedViewer.query.filter_by(userID=current_user.id, channelID=channelID).all()
            for invite in inviteQuery:
                if invite.isValid():
                    return True
                else:
                    db.session.delete(invite)
                    db.session.commit()
    return False

def check_isCommentUpvoted(commentID):
    commentQuery = upvotes.commentUpvotes.query.filter_by(commentID=int(commentID), userID=current_user.id).first()
    if commentQuery != None:
        return True
    else:
        return False

@asynch
def runWebhook(channelID, triggerType, **kwargs):
    webhookQuery = webhook.webhook.query.filter_by(channelID=channelID, requestTrigger=triggerType).all()

    if webhookQuery != []:
        for hook in webhookQuery:
            url = hook.endpointURL
            payload = processWebhookVariables(hook.requestPayload, **kwargs)
            header = json.loads(hook.requestHeader)
            requestType = hook.requestType
            try:
                if requestType == 0:
                    r = requests.post(url, headers=header, data=payload)
                elif requestType == 1:
                    r = requests.get(url, headers=header, data=payload)
                elif requestType == 2:
                    r = requests.put(url, headers=header, data=payload)
                elif requestType == 3:
                    r = requests.delete(url, headers=header, data=payload)
            except:
                pass
    db.session.commit()
    db.session.close()

def processWebhookVariables(payload, **kwargs):
    for key, value in kwargs.items():
        replacementValue = ("%" + key + "%")
        payload = payload.replace(replacementValue, str(value))
    return payload

app.jinja_env.globals.update(check_isValidChannelViewer=check_isValidChannelViewer)
app.jinja_env.globals.update(check_isCommentUpvoted=check_isCommentUpvoted)
### Start Jinja2 Filters

@app.context_processor
def inject_user_info():
    return dict(user=current_user)


@app.context_processor
def inject_sysSettings():
    db.session.commit()
    sysSettings = db.session.query(settings.settings).first()

    return dict(sysSettings=sysSettings)


@app.template_filter('normalize_uuid')
def normalize_uuid(uuidstr):
    return uuidstr.replace("-", "")


@app.template_filter('normalize_date')
def normalize_date(dateStr):
    return str(dateStr)[:19]

@app.template_filter('limit_title')
def limit_title(titleStr):
    if len(titleStr) > 40:
        return titleStr[:37] + "..."
    else:
        return titleStr


@app.template_filter('hms_format')
def hms_format(seconds):
    val = "Unknown"

    if seconds != None:
        val = time.strftime("%H:%M:%S", time.gmtime(seconds))
    return val

@app.template_filter('get_topicName')
def get_topicName(topicID):
    topicQuery = topics.topics.query.filter_by(id=int(topicID)).first()
    if topicQuery == None:
        return "None"
    return topicQuery.name


@app.template_filter('get_userName')
def get_userName(userID):
    userQuery = Sec.User.query.filter_by(id=int(userID)).first()
    return userQuery.username

@app.template_filter('get_Video_Upvotes')
def get_Video_Upvotes_Filter(videoID):
    result = get_Video_Upvotes(videoID)
    return result

@app.template_filter('get_Stream_Upvotes')
def get_Stream_Upvotes_Filter(videoID):
    result = get_Stream_Upvotes(videoID)
    return result

@app.template_filter('get_pictureLocation')
def get_pictureLocation(userID):
    userQuery = Sec.User.query.filter_by(id=int(userID)).first()
    pictureLocation = None
    if userQuery.pictureLocation == None:
        pictureLocation = '/static/img/user2.png'
    else:
        pictureLocation = '/images/' + userQuery.pictureLocation

    return pictureLocation


@app.template_filter('get_diskUsage')
def get_diskUsage(channelLocation):

    channelLocation = '/var/www/videos/' + channelLocation

    total_size = 0
    for dirpath, dirnames, filenames in os.walk(channelLocation):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return "{:,}".format(total_size)

@app.template_filter('get_webhookTrigger')
def get_webhookTrigger(webhookTrigger):

    webhookTrigger = str(webhookTrigger)
    webhookNames = {
        '0': 'Stream Start',
        '1': 'Stream End',
        '2': 'Stream Viewer Join',
        '3': 'Stream Viewer Upvote',
        '4': 'Stream Name Change',
        '5': 'Chat Message',
        '6': 'New Video',
        '7': 'Video Comment',
        '8': 'Video Upvote',
        '9': 'Video Name Change'
    }
    return webhookNames[webhookTrigger]


@user_registered.connect_via(app)
def user_registered_sighandler(app, user, confirm_token):
    default_role = user_datastore.find_role("User")
    user_datastore.add_role_to_user(user, default_role)
    db.session.commit()

### Start Error Handling ###

@app.errorhandler(404)
def page_not_found(e):
    sysSettings = settings.settings.query.first()
    return render_template('themes/' + sysSettings.systemTheme + '/404.html', sysSetting=sysSettings), 404

@app.errorhandler(500)
def page_not_found(e):
    sysSettings = settings.settings.query.first()
    return render_template('themes/' + sysSettings.systemTheme + '/500.html', sysSetting=sysSettings, error=e), 500


@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

### Start Flask Routes ###

@app.route('/')
def main_page():

    firstRunCheck = check_existing_users()

    if firstRunCheck is False:
        return render_template('/firstrun.html')

    else:
        sysSettings = settings.settings.query.first()
        activeStreams = Stream.Stream.query.order_by(Stream.Stream.currentViewers).all()

        randomRecorded = RecordedVideo.RecordedVideo.query.filter_by(pending=False).order_by(func.random()).limit(16)

        return render_template('themes/' + sysSettings.systemTheme + '/index.html', streamList=activeStreams, randomRecorded=randomRecorded)

@app.route('/channels')
def channels_page():
    sysSettings = settings.settings.query.first()
    if sysSettings.showEmptyTables == True:
        channelList = Channel.Channel.query.all()
    else:
        channelList = []
        for channel in Channel.Channel.query.all():
            if len(channel.recordedVideo) > 0:
                channelList.append(channel)
    return render_template('themes/' + sysSettings.systemTheme + '/channels.html', channelList=channelList)


@app.route('/channel/<chanID>/')
def channel_view_page(chanID):
    sysSettings = settings.settings.query.first()
    chanID = int(chanID)
    channelData = Channel.Channel.query.filter_by(id=chanID).first()

    if channelData != None:

        openStreams = Stream.Stream.query.filter_by(linkedChannel=chanID).all()
        recordedVids = RecordedVideo.RecordedVideo.query.filter_by(channelID=chanID, pending=False).all()

        # Sort Video to Show Newest First
        recordedVids.sort(key=lambda x: x.videoDate, reverse=True)
        return render_template('themes/' + sysSettings.systemTheme + '/videoListView.html', channelData=channelData, openStreams=openStreams, recordedVids=recordedVids, title="Channels - Videos")
    else:
        flash("No Such Channel", "error")
        return redirect(url_for("main_page"))


@app.route('/topics')
def topic_page():
    sysSettings = settings.settings.query.first()
    if sysSettings.showEmptyTables == True:
        topicsList = topics.topics.query.all()
    else:
        topicIDList = []
        for streamInstance in db.session.query(Stream.Stream.topic).distinct():
            topicIDList.append(streamInstance.topic)
        for recordedVidInstance in db.session.query(RecordedVideo.RecordedVideo.topic).distinct():
            if recordedVidInstance.topic not in topicIDList:
                topicIDList.append(recordedVidInstance.topic)

        topicsList = []

        for item in topicIDList:
            topicQuery = topics.topics.query.filter_by(id=item).first()
            if topicQuery != None:
                topicsList.append(topicQuery)

    return render_template('themes/' + sysSettings.systemTheme + '/topics.html', topicsList=topicsList)


@app.route('/topic/<topicID>/')
def topic_view_page(topicID):
    sysSettings = settings.settings.query.first()
    topicID = int(topicID)
    streamsQuery = Stream.Stream.query.filter_by(topic=topicID).all()
    recordedVideoQuery = RecordedVideo.RecordedVideo.query.filter_by(topic=topicID, pending=False).all()

    # Sort Video to Show Newest First
    recordedVideoQuery.sort(key=lambda x: x.videoDate, reverse=True)

    return render_template('themes/' + sysSettings.systemTheme + '/videoListView.html', openStreams=streamsQuery, recordedVids=recordedVideoQuery, title="Topics - Videos")

@app.route('/streamers')
def streamers_page():
    sysSettings = settings.settings.query.first()
    streamerIDs = []

    if sysSettings.showEmptyTables == True:
        for channel in db.session.query(Channel.Channel.owningUser).distinct():
            if channel.owningUser not in streamerIDs:
                streamerIDs.append(channel.owningUser)
    else:
        openStreams = Stream.Stream.query.all()
        for stream in openStreams:
            if stream.channel.owningUser not in streamerIDs:
                streamerIDs.append(stream.channel.owningUser)
        for recordedVidInstance in db.session.query(RecordedVideo.RecordedVideo.owningUser).distinct():
            if recordedVidInstance.owningUser not in streamerIDs:
                streamerIDs.append(recordedVidInstance.owningUser)

    streamerList = []
    for userID in streamerIDs:
        userQuery = Sec.User.query.filter_by(id=userID).first()
        if userQuery != None:
            streamerList.append(userQuery)

    return render_template('themes/' + sysSettings.systemTheme + '/streamers.html', streamerList=streamerList)

@app.route('/streamers/<userID>/')
def streamers_view_page(userID):
    sysSettings = settings.settings.query.first()
    userID = int(userID)

    userName = Sec.User.query.filter_by(id=userID).first().username

    userChannels = Channel.Channel.query.filter_by(owningUser=userID).all()

    streams = []

    for channel in userChannels:
        for stream in channel.stream:
            streams.append(stream)

    recordedVideoQuery = RecordedVideo.RecordedVideo.query.filter_by(owningUser=userID, pending=False).all()

    # Sort Video to Show Newest First
    recordedVideoQuery.sort(key=lambda x: x.videoDate, reverse=True)

    return render_template('themes/' + sysSettings.systemTheme + '/videoListView.html', openStreams=streams, recordedVids=recordedVideoQuery, title=userName + " - Videos")

# Allow a direct link to any open stream for a channel
@app.route('/channel/<loc>/stream')
def channel_stream_link_page(loc):
    requestedChannel = Channel.Channel.query.filter_by(id=int(loc)).first()
    if requestedChannel != None:
        openStreamQuery = Stream.Stream.query.filter_by(linkedChannel=requestedChannel.id).first()
        if openStreamQuery != None:
            return redirect(url_for("view_page", loc=requestedChannel.channelLoc))
        else:
            flash("No Active Streams for the Channel","error")
            return redirect(url_for("channel_view_page",chanID=requestedChannel.id))
    else:
        flash("Unknown Channel","error")
        return redirect(url_for("main_page"))

@app.route('/view/<loc>/')
def view_page(loc):
    sysSettings = settings.settings.query.first()

    requestedChannel = Channel.Channel.query.filter_by(channelLoc=loc).first()

    if requestedChannel.protected:
        if not check_isValidChannelViewer(requestedChannel.id):
            return render_template('themes/' + sysSettings.systemTheme + '/channelProtectionAuth.html')

    global streamUserList

    if requestedChannel.channelLoc not in streamUserList:
        streamUserList[requestedChannel.channelLoc] = []

    streamData = Stream.Stream.query.filter_by(streamKey=requestedChannel.streamKey).first()

    if requestedChannel is not None:

        streamURL = ''
        if sysSettings.adaptiveStreaming is True:
            streamURL = '/live-adapt/' + requestedChannel.channelLoc + '.m3u8'
        elif requestedChannel.record is True:
            streamURL = '/live-rec/' + requestedChannel.channelLoc + '/index.m3u8'
        elif requestedChannel.record is False:
            streamURL = '/live/' + requestedChannel.channelLoc + '/index.m3u8'

        requestedChannel.views = requestedChannel.views + 1
        if streamData is not None:
            streamData.totalViewers = streamData.totalViewers + 1
        db.session.commit()

        topicList = topics.topics.query.all()

        chatOnly = request.args.get("chatOnly")

        if chatOnly == "True" or chatOnly == "true":
            if requestedChannel.chatEnabled == True:
                return render_template('themes/' + sysSettings.systemTheme + '/chatpopout.html', stream=streamData, streamURL=streamURL, sysSettings=sysSettings, channel=requestedChannel)
            else:
                flash("Chat is Not Enabled For This Stream","error")

        isEmbedded = request.args.get("embedded")

        newView = views.views(0, requestedChannel.id)
        db.session.add(newView)
        db.session.commit()

        if isEmbedded == None or isEmbedded == "False":
            randomRecorded = RecordedVideo.RecordedVideo.query.filter_by(pending=False, channelID=requestedChannel.id).order_by(func.random()).limit(16)
            return render_template('themes/' + sysSettings.systemTheme + '/channelplayer.html', stream=streamData, streamURL=streamURL, topics=topicList, randomRecorded=randomRecorded, channel=requestedChannel)
        else:
            isAutoPlay = request.args.get("autoplay")
            if isAutoPlay == None:
                isAutoPlay = False
            elif isAutoPlay.lower() == 'true':
                isAutoPlay = True
            else:
                isAutoPlay = False
            return render_template('themes/' + sysSettings.systemTheme + '/player_embed.html', stream=streamData, streamURL=streamURL, topics=topicList, isAutoPlay=isAutoPlay)

    else:
        flash("No Live Stream at URL","error")
        return redirect(url_for("main_page"))


@app.route('/play/<videoID>')
def view_vid_page(videoID):
    sysSettings = settings.settings.query.first()

    recordedVid = RecordedVideo.RecordedVideo.query.filter_by(id=videoID).first()

    if recordedVid.channel.protected:
        if not check_isValidChannelViewer(recordedVid.channel.id):
            return render_template('themes/' + sysSettings.systemTheme + '/channelProtectionAuth.html')

    if recordedVid != None:
        recordedVid.views = recordedVid.views + 1
        recordedVid.channel.views = recordedVid.channel.views + 1

        if recordedVid.length == None:
            fullVidPath = '/var/www/videos/' + recordedVid.videoLocation
            duration = getVidLength(fullVidPath)
            recordedVid.length = duration
        db.session.commit()

        topicList = topics.topics.query.all()

        streamURL = '/videos/' + recordedVid.videoLocation

        isEmbedded = request.args.get("embedded")

        newView = views.views(1, recordedVid.id)
        db.session.add(newView)
        db.session.commit()

        if isEmbedded == None or isEmbedded == "False":

            randomRecorded = RecordedVideo.RecordedVideo.query.filter_by(pending=False, channelID=recordedVid.channel.id).order_by(func.random()).limit(12)

            return render_template('themes/' + sysSettings.systemTheme + '/vidplayer.html', video=recordedVid, streamURL=streamURL, topics=topicList, randomRecorded=randomRecorded)
        else:
            isAutoPlay = request.args.get("autoplay")
            if isAutoPlay == None:
                isAutoPlay = False
            elif isAutoPlay.lower() == 'true':
                isAutoPlay = True
            else:
                isAutoPlay = False
            return render_template('themes/' + sysSettings.systemTheme + '/vidplayer_embed.html', video=recordedVid, streamURL=streamURL, topics=topicList, isAutoPlay=isAutoPlay)
    else:
        flash("No Such Video at URL","error")
        return redirect(url_for("main_page"))

@app.route('/play/<loc>/move', methods=['POST'])
@login_required
def vid_move_page(loc):
    recordedVidQuery = RecordedVideo.RecordedVideo.query.filter_by(id=loc, owningUser=current_user.id).first()
    sysSettings = settings.settings.query.first()

    if recordedVidQuery != None:
        newChannel = int(request.form['moveToChannelID'])
        newChannelQuery = Channel.Channel.query.filter_by(id=newChannel, owningUser=current_user.id).first()
        if newChannelQuery != None:
            recordedVidQuery.channelID = newChannelQuery.id
            coreVideo = (recordedVidQuery.videoLocation.split("/")[1]).split("_", 1)[1]
            if os.path.isdir("/var/www/videos/" + newChannelQuery.channelLoc):
                shutil.move("/var/www/videos/" + recordedVidQuery.videoLocation, "/var/www/videos/" + newChannelQuery.channelLoc + "/" + newChannelQuery.channelLoc + "_" + coreVideo)
                recordedVidQuery.videoLocation = newChannelQuery.channelLoc + "/" + newChannelQuery.channelLoc + "_" + coreVideo
                if (recordedVidQuery.thumbnailLocation != None) and (os.path.exists("/var/www/videos/" + recordedVidQuery.thumbnailLocation)):
                    coreThumbnail = (recordedVidQuery.thumbnailLocation.split("/")[1]).split("_", 1)[1]
                    shutil.move("/var/www/videos/" + recordedVidQuery.thumbnailLocation,"/var/www/videos/" + newChannelQuery.channelLoc + "/" + newChannelQuery.channelLoc + "_" + coreThumbnail)
                    recordedVidQuery.thumbnailLocation = newChannelQuery.channelLoc + "/" + newChannelQuery.channelLoc + "_" + coreThumbnail

                db.session.commit()
                flash("Video Moved to Another Channel", "success")
                return redirect(url_for('view_vid_page', videoID=loc))

    flash("Error Moving Video", "error")
    return redirect(url_for("main_page"))

@app.route('/play/<loc>/change', methods=['POST'])
@login_required
def vid_change_page(loc):

    recordedVidQuery = RecordedVideo.RecordedVideo.query.filter_by(id=loc, owningUser=current_user.id).first()
    sysSettings = settings.settings.query.first()

    if recordedVidQuery != None:

        newVidName = strip_html(request.form['newVidName'])
        newVidTopic = request.form['newVidTopic']
        description = request.form['description']

        allowComments = False
        if 'allowComments' in request.form:
            allowComments = True

        if recordedVidQuery is not None:
            recordedVidQuery.channelName = strip_html(newVidName)
            recordedVidQuery.topic = newVidTopic
            recordedVidQuery.description = strip_html(description)
            recordedVidQuery.allowComments = allowComments

            if recordedVidQuery.channel.imageLocation is None:
                channelImage = (sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
            else:
                channelImage = (sysSettings.siteAddress + "/images/" + recordedVidQuery.channel.imageLocation)

            runWebhook(recordedVidQuery.channel.id, 9, channelname=recordedVidQuery.channel.channelName,
                       channelurl=(sysSettings.siteAddress + "/channel/" + str(recordedVidQuery.channel.id)),
                       channeltopic=get_topicName(recordedVidQuery.channel.topic),
                       channelimage=channelImage, streamer=get_userName(recordedVidQuery.channel.owningUser),
                       channeldescription=recordedVidQuery.channel.description, videoname=recordedVidQuery.channelName,
                       videodate=recordedVidQuery.videoDate, videodescription=recordedVidQuery.description,
                       videotopic=get_topicName(recordedVidQuery.topic),
                       videourl=(sysSettings.siteAddress + '/videos/' + recordedVidQuery.videoLocation),
                       videothumbnail=(sysSettings.siteAddress + '/videos/' + recordedVidQuery.thumbnailLocation))
            db.session.commit()

        return redirect(url_for('view_vid_page', videoID=loc))
    else:
        flash("Error Changing Video Metadata", "error")
        return redirect(url_for("main_page"))


@app.route('/play/<videoID>/delete')
@login_required
def delete_vid_page(videoID):

    recordedVid = RecordedVideo.RecordedVideo.query.filter_by(id=videoID).first()

    if current_user.id == recordedVid.owningUser and recordedVid.videoLocation != None:
        filePath = '/var/www/videos/' + recordedVid.videoLocation
        thumbnailPath = '/var/www/videos/' + recordedVid.videoLocation[:-4] + ".png"

        if filePath != '/var/www/videos/':
            if os.path.exists(filePath) and (recordedVid.videoLocation != None or recordedVid.videoLocation != ""):
                os.remove(filePath)
                if os.path.exists(thumbnailPath):
                    os.remove(thumbnailPath)

        # Delete Upvotes Attached to Video
        upvoteQuery = upvotes.videoUpvotes.query.filter_by(videoID=recordedVid.id).all()

        for vote in upvoteQuery:
            db.session.delete(vote)

        # Delete Comments Attached to Video
        commentQuery = comments.videoComments.query.filter_by(videoID=recordedVid.id).all()

        for comment in commentQuery:
            db.session.delete(comment)

        # Delete Views Attached to Video
        viewQuery = views.views.query.filter_by(viewType=1, itemID=recordedVid.id).all()

        for view in viewQuery:
            db.session.delete(view)

        db.session.delete(recordedVid)

        db.session.commit()

        return redirect(url_for('main_page'))
    else:
        flash("Error Deleting Video")
        return redirect(url_for('view_vid_page', videoID=videoID))

@app.route('/play/<videoID>/comment', methods=['GET','POST'])
@login_required
def comments_vid_page(videoID):
    sysSettings = settings.settings.query.first()

    recordedVid = RecordedVideo.RecordedVideo.query.filter_by(id=videoID).first()

    if recordedVid != None:

        if request.method == 'POST':

            comment = strip_html(request.form['commentText'])
            currentUser = current_user.id

            newComment = comments.videoComments(currentUser,comment,recordedVid.id)
            db.session.add(newComment)
            db.session.commit()

            if recordedVid.channel.imageLocation is None:
                channelImage = (sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
            else:
                channelImage = (sysSettings.siteAddress + "/images/" + recordedVid.channel.imageLocation)

            pictureLocation = ""
            if current_user.pictureLocation == None:
                pictureLocation = '/static/img/user2.png'
            else:
                pictureLocation = '/images/' + pictureLocation

            runWebhook(recordedVid.channel.id, 7, channelname=recordedVid.channel.channelName,
                       channelurl=(sysSettings.siteAddress + "/channel/" + str(recordedVid.channel.id)),
                       channeltopic=get_topicName(recordedVid.channel.topic),
                       channelimage=channelImage, streamer=get_userName(recordedVid.channel.owningUser),
                       channeldescription=recordedVid.channel.description, videoname=recordedVid.channelName,
                       videodate=recordedVid.videoDate, videodescription=recordedVid.description,
                       videotopic=get_topicName(recordedVid.topic),
                       videourl=(sysSettings.siteAddress + '/videos/' + recordedVid.videoLocation),
                       videothumbnail=(sysSettings.siteAddress + '/videos/' + recordedVid.thumbnailLocation),
                       user=current_user.username, userpicture=(sysSettings.siteAddress + pictureLocation), comment=comment)
            flash('Comment Added', "success")

        elif request.method == 'GET':
            if request.args.get('action') == "delete":
                commentID = int(request.args.get('commentID'))
                commentQuery = comments.videoComments.query.filter_by(id=commentID).first()
                if commentQuery != None:
                    if current_user.has_role('Admin') or recordedVid.owningUser == current_user.id or commentQuery.userID == current_user.id:
                        upvoteQuery = upvotes.commentUpvotes.query.filter_by(commentID=commentQuery.id).all()
                        for vote in upvoteQuery:
                            db.session.delete(vote)
                        db.session.delete(commentQuery)
                        db.session.commit()
                        flash('Comment Deleted', "success")
                    else:
                        flash("Not Authorized to Remove Comment", "error")

    else:
        flash('Invalid Video ID','error')
        return redirect(url_for('main_page'))

    return redirect(url_for('view_vid_page', videoID=videoID))


@app.route('/settings/user', methods=['POST','GET'])
@login_required
def user_page():
    if request.method == 'GET':
        sysSettings = settings.settings.query.first()
        return render_template('themes/' + sysSettings.systemTheme + '/userSettings.html')
    elif request.method == 'POST':
        emailAddress = request.form['emailAddress']
        password1 = request.form['password1']
        password2 = request.form['password2']

        if password1 != "":
            if password1 == password2:
                newPassword = hash_password(password1)
                current_user.password = newPassword
                flash("Password Changed")
            else:
                flash("Passwords Don't Match!")

        if 'photo' in request.files:
            oldImage = None

            if current_user.pictureLocation != None:
                oldImage = current_user.pictureLocation

            filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')
            current_user.pictureLocation = filename

            if oldImage != None:
                try:
                    os.remove(oldImage)
                except OSError:
                    pass

        current_user.emailAddress = emailAddress

        db.session.commit()

    return redirect(url_for('user_page'))

@app.route('/settings/user/addInviteCode')
@login_required
def user_addInviteCode():
    if 'inviteCode' in request.args:
        inviteCode = request.args.get("inviteCode")
        inviteCodeQuery = invites.inviteCode.query.filter_by(code=inviteCode).first()
        if inviteCodeQuery is not None:
            if inviteCodeQuery.isValid():
                existingInviteQuery = invites.invitedViewer.query.filter_by(inviteCode=inviteCodeQuery.id, userID=current_user.id).first()
                if existingInviteQuery is None:
                    if inviteCodeQuery.expiration != None:
                        remainingDays = (inviteCodeQuery.expiration - datetime.datetime.now()).days
                    else:
                        remainingDays = 0
                    newInvitedUser = invites.invitedViewer(current_user.id, inviteCodeQuery.channelID, remainingDays, inviteCode=inviteCodeQuery.id)
                    inviteCodeQuery.uses = inviteCodeQuery.uses + 1
                    db.session.add(newInvitedUser)
                    db.session.commit()
                    flash("Added Invite Code to Channel", "success")
                    if 'redirectURL' in request.args:
                        return redirect(request.args.get("redirectURL"))
                else:
                    flash("Invite Code Already Applied", "error")
            else:
                flash("Invite Code Expired", "error")
        else:
            flash("Invalid Invite Code", "error")
    return redirect(url_for('main_page'))


@app.route('/settings/admin', methods=['POST','GET'])
@login_required
@roles_required('Admin')
def admin_page():
    sysSettings = settings.settings.query.first()
    if request.method == 'GET':
        if request.args.get("action") is not None:
            action = request.args.get("action")
            setting = request.args.get("setting")

            if action == "delete":
                if setting == "topics":
                    topicID = int(request.args.get("topicID"))

                    topicQuery = topics.topics.query.filter_by(id=topicID).first()

                    channels = Channel.Channel.query.filter_by(topic=topicID).all()
                    videos = RecordedVideo.RecordedVideo.query.filter_by(topic=topicID).all()

                    defaultTopic = topics.topics.query.filter_by(name="Other").first()

                    for chan in channels:
                        chan.topic = defaultTopic.id
                    for vid in videos:
                        vid.topic = defaultTopic.id

                    db.session.delete(topicQuery)
                    db.session.commit()
                    flash("Topic Deleted")

                elif setting == "channel":
                    channelID = int(request.args.get("channelID"))

                    channelQuery = Channel.Channel.query.filter_by(id=channelID).first()

                    for vid in channelQuery.recordedVideo:
                        for upvote in vid.upvotes:
                            db.session.delete(upvote)

                        vidComments = vid.comments
                        for comment in vidComments:
                            db.session.delete(comment)

                        vidViews = views.views.query.filter_by(viewType=1, itemID=vid.id)
                        for view in vidViews:
                            db.session.delete(view)

                        db.session.delete(vid)
                    for upvote in channelQuery.upvotes:
                        db.session.delete(upvote)


                    filePath = '/var/www/videos/' + channelQuery.channelLoc

                    if filePath != '/var/www/videos/':
                        shutil.rmtree(filePath, ignore_errors=True)

                    db.session.delete(channelQuery)
                    db.session.commit()
                    flash("Channel Deleted")

                elif setting == "users":
                    userID = int(request.args.get("userID"))

                    userQuery = Sec.User.query.filter_by(id=userID).first()

                    if userQuery != None:

                        channelQuery = Channel.Channel.query.filter_by(owningUser=userQuery.id).all()

                        for chan in channelQuery:

                            for vid in chan.recordedVideo:
                                for upvote in vid.upvotes:
                                    db.session.delete(upvote)

                                vidComments = vid.comments
                                for comment in vidComments:
                                    db.session.delete(comment)

                                vidViews = views.views.query.filter_by(viewType=1, itemID=vid.id)
                                for view in vidViews:
                                    db.session.delete(view)

                                db.session.delete(vid)
                            for upvote in chan.upvotes:
                                db.session.delete(upvote)

                            filePath = '/var/www/videos/' + chan.channelLoc

                            if filePath != '/var/www/videos/':
                                shutil.rmtree(filePath, ignore_errors=True)

                            db.session.delete(chan)

                        db.session.delete(userQuery)
                        db.session.commit()
                        flash("User " + str(userQuery.username) + " Deleted")

                elif setting == "userRole":
                    userID = int(request.args.get("userID"))
                    roleID = int(request.args.get("roleID"))

                    userQuery = Sec.User.query.filter_by(id=userID).first()
                    roleQuery = Sec.Role.query.filter_by(id=roleID).first()

                    if userQuery != None and roleQuery != None:
                        user_datastore.remove_role_from_user(userQuery,roleQuery.name)
                        db.session.commit()
                        flash("Removed Role from User")

                    else:
                        flash("Invalid Role or User!")

            elif action == "add":
                if setting == "userRole":
                    userID = int(request.args.get("userID"))
                    roleName = str(request.args.get("roleName"))

                    userQuery = Sec.User.query.filter_by(id=userID).first()
                    roleQuery = Sec.Role.query.filter_by(name=roleName).first()

                    if userQuery != None and roleQuery != None:
                        user_datastore.add_role_to_user(userQuery, roleQuery.name)
                        db.session.commit()
                        flash("Added Role to User")
                    else:
                        flash("Invalid Role or User!")
            elif action == "toggleActive":
                if setting == "users":
                    userID = int(request.args.get("userID"))
                    userQuery = Sec.User.query.filter_by(id=userID).first()
                    if userQuery != None:
                        if userQuery.active == True:
                            userQuery.active = False
                            flash("User Disabled")
                        else:
                            userQuery.active = True
                            flash("User Enabled")
                        db.session.commit()

            return redirect(url_for('admin_page'))

        repoSHA = "N/A"
        remoteSHA = repoSHA
        branch = "Local Install"
        validGitRepo = False
        try:
            repo = git.Repo(search_parent_directories=True)
            validGitRepo = True
        except:
            pass

        if validGitRepo == True:
            remoteSHA = None
            if repo != None:
                repoSHA = str(repo.head.object.hexsha)
                branch = repo.active_branch
                branch = branch.name
                remote = repo.remotes.origin.fetch()[0].commit
                remoteSHA = str(remote)


        appDBVer = dbVersion.dbVersion.query.first().version
        userList = Sec.User.query.all()
        roleList = Sec.Role.query.all()
        channelList = Channel.Channel.query.all()
        streamList = Stream.Stream.query.all()
        topicsList = topics.topics.query.all()

        # 30 Days Viewer Stats
        viewersTotal = 0

        # Create List of 30 Day Viewer Stats
        statsViewsLiveDay = db.session.query(func.date(views.views.date), func.count(views.views.id)).filter(views.views.viewType == 0).filter(views.views.date > (datetime.datetime.now() - datetime.timedelta(days=30))).group_by(func.date(views.views.date)).all()
        statsViewsLiveDayArray = []
        for entry in statsViewsLiveDay:
            viewersTotal = viewersTotal + entry[1]
            statsViewsLiveDayArray.append({'t': (entry[0]), 'y': entry[1]})

        statsViewsRecordedDay = db.session.query(func.date(views.views.date), func.count(views.views.id)).filter(views.views.viewType == 1).filter(views.views.date > (datetime.datetime.now() - datetime.timedelta(days=30))).group_by(func.date(views.views.date)).all()
        statsViewsRecordedDayArray = []

        for entry in statsViewsRecordedDay:
            viewersTotal = viewersTotal + entry[1]
            statsViewsRecordedDayArray.append({'t': (entry[0]), 'y': entry[1]})

        statsViewsDay = {
            'live': statsViewsLiveDayArray,
            'recorded': statsViewsRecordedDayArray
        }

        currentViewers = 0
        for stream in streamList:
            currentViewers = currentViewers + stream.currentViewers

        themeList = []
        themeDirectorySearch = os.listdir("./templates/themes/")
        for theme in themeDirectorySearch:
            hasJSON = os.path.isfile("./templates/themes/" + theme + "/theme.json")
            if hasJSON:
                themeList.append(theme)

        return render_template('themes/' + sysSettings.systemTheme + '/admin.html', appDBVer=appDBVer, userList=userList, roleList=roleList, channelList=channelList, streamList=streamList, topicsList=topicsList, repoSHA=repoSHA,repoBranch=branch, remoteSHA=remoteSHA, themeList=themeList, statsViewsDay=statsViewsDay, viewersTotal=viewersTotal, currentViewers=currentViewers)
    elif request.method == 'POST':

        settingType = request.form['settingType']

        if settingType == "system":

            serverName = request.form['serverName']
            serverAddress = request.form['serverAddress']
            smtpSendAs = request.form['smtpSendAs']
            smtpAddress = request.form['smtpAddress']
            smtpPort = request.form['smtpPort']
            smtpUser = request.form['smtpUser']
            smtpPassword = request.form['smtpPassword']
            theme = request.form['theme']

            recordSelect = False
            registerSelect = False
            emailValidationSelect = False
            adaptiveStreaming = False
            showEmptyTables = False
            allowComments = False
            smtpTLS = False
            smtpSSL = False

            if 'recordSelect' in request.form:
                recordSelect = True

            if 'registerSelect' in request.form:
                registerSelect = True

            if 'emailValidationSelect' in request.form:
                emailValidationSelect = True

            if 'adaptiveStreaming' in request.form:
                adaptiveStreaming = True

            if 'showEmptyTables' in request.form:
                showEmptyTables = True

            if 'allowComments' in request.form:
                allowComments = True

            if 'smtpTLS' in request.form:
                smtpTLS = True

            if 'smtpSSL' in request.form:
                smtpSSL = True

            systemLogo = None
            if 'photo' in request.files:
                file = request.files['photo']
                if file.filename != '':
                    filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')
                    systemLogo = filename

            sysSettings.siteName = serverName
            sysSettings.siteAddress = serverAddress
            sysSettings.smtpSendAs = smtpSendAs
            sysSettings.smtpAddress = smtpAddress
            sysSettings.smtpPort = smtpPort
            sysSettings.smtpUsername = smtpUser
            sysSettings.smtpPassword = smtpPassword
            sysSettings.smtpTLS = smtpTLS
            sysSettings.smtpSSL = smtpSSL
            sysSettings.allowRecording = recordSelect
            sysSettings.allowRegistration = registerSelect
            sysSettings.requireConfirmedEmail = emailValidationSelect
            sysSettings.adaptiveStreaming = adaptiveStreaming
            sysSettings.showEmptyTables = showEmptyTables
            sysSettings.allowComments = allowComments
            sysSettings.systemTheme = theme
            sysSettings.systemLogo = systemLogo

            db.session.commit()

            sysSettings = settings.settings.query.first()

            app.config.update(
                SERVER_NAME=None,
                SECURITY_EMAIL_SENDER=sysSettings.smtpSendAs,
                MAIL_SERVER=sysSettings.smtpAddress,
                MAIL_PORT=sysSettings.smtpPort,
                MAIL_USE_SSL=sysSettings.smtpSSL,
                MAIL_USE_TLS=sysSettings.smtpTLS,
                MAIL_USERNAME=sysSettings.smtpUsername,
                MAIL_PASSWORD=sysSettings.smtpPassword,
                SECURITY_REGISTERABLE=sysSettings.allowRegistration,
                SECURITY_CONFIRMABLE = sysSettings.requireConfirmedEmail,
                SECURITY_SEND_REGISTER_EMAIL = sysSettings.requireConfirmedEmail,
                SECURITY_EMAIL_SUBJECT_PASSWORD_RESET = sysSettings.siteName + " - Password Reset Request",
                SECURITY_EMAIL_SUBJECT_REGISTER = sysSettings.siteName + " - Welcome!",
                SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE = sysSettings.siteName + " - Password Reset Notification",
                SECURITY_EMAIL_SUBJECT_CONFIRM = sysSettings.siteName + " - Email Confirmation Request",
                SECURITY_FORGOT_PASSWORD_TEMPLATE = 'themes/' + sysSettings.systemTheme + '/security/forgot_password.html',
                SECURITY_LOGIN_USER_TEMPLATE = 'themes/' + sysSettings.systemTheme + '/security/login_user.html',
                SECURITY_REGISTER_USER_TEMPLATE = 'themes/' + sysSettings.systemTheme + '/security/register_user.html',
                SECURITY_RESET_PASSWORD_TEMPLATE = 'themes/' + sysSettings.systemTheme + '/security/reset_password.html',
                SECURITY_SEND_CONFIRMATION_TEMPLATE = 'themes/'  + sysSettings.systemTheme + '/security/send_confirmation.html')

            global mail
            mail = Mail(app)

        elif settingType == "topics":

            if 'topicID' in request.form:
                topicID = int(request.form['topicID'])
                topicName = request.form['name']

                topicQuery = topics.topics.query.filter_by(id=topicID).first()

                if topicQuery != None:

                    topicQuery.name = topicName

                    if 'photo' in request.files:
                        file = request.files['photo']
                        if file.filename != '':
                            oldImage = None

                            if topicQuery.iconClass != None:
                                oldImage = topicQuery.iconClass

                            filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')
                            topicQuery.iconClass = filename

                            if oldImage != None:
                                try:
                                    os.remove(oldImage)
                                except OSError:
                                    pass
            else:
                topicName = request.form['name']

                topicImage = None
                if 'photo' in request.files:
                    file = request.files['photo']
                    if file.filename != '':
                        filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')
                        topicImage = filename

                newTopic = topics.topics(topicName, topicImage)
                db.session.add(newTopic)

            db.session.commit()

        return redirect(url_for('admin_page'))


@app.route('/settings/channels', methods=['POST','GET'])
@login_required
def settings_channels_page():
    sysSettings = settings.settings.query.first()
    channelChatBGOptions = [{'name': 'Default', 'value': 'Standard'}, {'name': 'Deep Space', 'value': 'DeepSpace'}, {'name': 'Blood Red', 'value': 'BloodRed'}, {'name': 'Terminal', 'value': 'Terminal'}]
    channelChatAnimationOptions = [{'name':'No Animation', 'value':'None'},{'name': 'Slide-in From Left', 'value': 'slide-in-left'}, {'name':'Slide-In Blurred From Left','value':'slide-in-blurred-left'}, {'name':'Fade-In', 'value': 'fade-in-fwd'}]

    if request.method == 'GET':
        if request.args.get("action") is not None:
            action = request.args.get("action")
            streamKey = request.args.get("streamkey")

            requestedChannel = Channel.Channel.query.filter_by(streamKey=streamKey).first()

            if action == "delete":
                if current_user.id == requestedChannel.owningUser:

                    filePath = '/var/www/videos/' + requestedChannel.channelLoc
                    if filePath != '/var/www/videos/':
                        shutil.rmtree(filePath, ignore_errors=True)

                    channelVid = requestedChannel.recordedVideo
                    channelUpvotes = requestedChannel.upvotes
                    channelStreams = requestedChannel.stream

                    for entry in channelVid:

                        vidComments = channelVid.comments
                        for comment in vidComments:
                            db.session.delete(comment)

                        vidViews = views.views.query.filter_by(viewType=1, itemID=channelVid.id)
                        for view in vidViews:
                            db.session.delete(view)

                        db.session.delete(entry)
                    for entry in channelUpvotes:
                        db.session.delete(entry)
                    for entry in channelStreams:
                        db.session.delete(entry)

                    db.session.delete(requestedChannel)
                    db.session.commit()
                    flash("Channel Deleted")
                else:
                    flash("Invalid Deletion Attempt","Error")

    elif request.method == 'POST':

        type = request.form['type']
        channelName = strip_html(request.form['channelName'])
        topic = request.form['channeltopic']
        description = strip_html(request.form['description'])

        record = False

        if 'recordSelect' in request.form and sysSettings.allowRecording is True:
            record = True

        chatEnabled = False

        if 'chatSelect' in request.form:
            chatEnabled = True

        allowComments = False

        if 'allowComments' in request.form:
            allowComments = True

        protection = False

        if 'channelProtection' in request.form:
            protection = True

        if type == 'new':

            newUUID = str(uuid.uuid4())

            newChannel = Channel.Channel(current_user.id, newUUID, channelName, topic, record, chatEnabled, allowComments, description)

            if 'photo' in request.files:
                file = request.files['photo']
                if file.filename != '':
                    filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')
                    newChannel.imageLocation = filename

            db.session.add(newChannel)
            db.session.commit()

        elif type == 'change':
            streamKey = request.form['streamKey']
            origStreamKey = request.form['origStreamKey']

            chatBG = request.form['chatBG']
            chatAnimation = request.form['chatAnimation']
            chatTextColor = request.form['chatTextColor']

            # TODO Validate ChatBG and chatAnimation

            requestedChannel = Channel.Channel.query.filter_by(streamKey=origStreamKey).first()

            if current_user.id == requestedChannel.owningUser:
                requestedChannel.channelName = channelName
                requestedChannel.streamKey = streamKey
                requestedChannel.topic = topic
                requestedChannel.record = record
                requestedChannel.chatEnabled = chatEnabled
                requestedChannel.allowComments = allowComments
                requestedChannel.description = description
                requestedChannel.chatBG = chatBG
                requestedChannel.chatAnimation = chatAnimation
                requestedChannel.chatTextColor = chatTextColor
                requestedChannel.protected = protection

                if 'photo' in request.files:
                    file = request.files['photo']
                    if file.filename != '':
                        oldImage = None

                        if requestedChannel.imageLocation != None:
                            oldImage = requestedChannel.imageLocation

                        filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')
                        requestedChannel.imageLocation = filename

                        if oldImage != None:
                            try:
                                os.remove(oldImage)
                            except OSError:
                                pass

                if 'offlinephoto' in request.files:
                    file = request.files['offlinephoto']
                    if file.filename != '':
                        oldImage = None

                        if requestedChannel.offlineImageLocation != None:
                            oldImage = requestedChannel.offlineImageLocation

                        filename = photos.save(request.files['offlinephoto'], name=str(uuid.uuid4()) + '.')
                        requestedChannel.offlineImageLocation = filename

                        if oldImage != None:
                            try:
                                os.remove(oldImage)
                            except OSError:
                                pass

                flash("Channel Edited")
                db.session.commit()
            else:
                flash("Invalid Change Attempt","Error")
            redirect(url_for('settings_channels_page'))

    topicList = topics.topics.query.all()
    user_channels = Channel.Channel.query.filter_by(owningUser = current_user.id).all()

    # Calculate Channel Views by Date based on Video or Live Views
    user_channels_stats = {}
    for channel in user_channels:

        # 30 Days Viewer Stats
        viewersTotal = 0

        statsViewsLiveDay = db.session.query(func.date(views.views.date), func.count(views.views.id)).filter(
            views.views.viewType == 0).filter(views.views.itemID == channel.id).filter(
            views.views.date > (datetime.datetime.now() - datetime.timedelta(days=30))).group_by(
            func.date(views.views.date)).all()
        statsViewsLiveDayArray = []
        for entry in statsViewsLiveDay:
            viewersTotal = viewersTotal + entry[1]
            statsViewsLiveDayArray.append({'t': (entry[0]), 'y': entry[1]})

        statsViewsRecordedDayDict = {}
        statsViewsRecordedDayArray = []

        for vid in channel.recordedVideo:
            statsViewsRecordedDay = db.session.query(func.date(views.views.date), func.count(views.views.id)).filter(
                views.views.viewType == 1).filter(views.views.itemID == vid.id).filter(
                views.views.date > (datetime.datetime.now() - datetime.timedelta(days=30))).group_by(
                func.date(views.views.date)).all()

            for entry in statsViewsRecordedDay:
                if entry[0] in statsViewsRecordedDayDict:
                    statsViewsRecordedDayDict[entry[0]] = statsViewsRecordedDayDict[entry[0]] + entry[1]
                else:
                    statsViewsRecordedDayDict[entry[0]] = entry[1]
                viewersTotal = viewersTotal + entry[1]

        for entry in statsViewsRecordedDayDict:
            statsViewsRecordedDayArray.append({'t': entry, 'y': statsViewsRecordedDayDict[entry]})

        sortedStatsArray = sorted(statsViewsRecordedDayArray, key=lambda d: d['t'])

        statsViewsDay = {
            'live': statsViewsLiveDayArray,
            'recorded': sortedStatsArray
        }

        user_channels_stats[channel.id] = statsViewsDay

    return render_template('themes/' + sysSettings.systemTheme + '/user_channels.html', channels=user_channels, topics=topicList, viewStats=user_channels_stats, channelChatBGOptions=channelChatBGOptions, channelChatAnimationOptions=channelChatAnimationOptions)

@app.route('/settings/api', methods=['GET'])
@login_required
@roles_required('Streamer')
def settings_apikeys_page():
    sysSettings = settings.settings.query.first()
    apiKeyQuery = apikey.apikey.query.filter_by(userID=current_user.id).all()
    return render_template('themes/' + sysSettings.systemTheme + '/apikeys.html',apikeys=apiKeyQuery)

@app.route('/settings/api/<string:action>', methods=['POST'])
@login_required
@roles_required('Streamer')
def settings_apikeys_post_page(action):
    if action == "new":
        newapi = apikey.apikey(current_user.id, 1, request.form['keyName'], request.form['expiration'])
        db.session.add(newapi)
        db.session.commit()
        flash("New API Key Added","success")
    elif action == "delete":
        apiQuery = apikey.apikey.query.filter_by(key=request.form['key']).first()
        if apiQuery.userID == current_user.id:
            db.session.delete(apiQuery)
            db.session.commit()
            flash("API Key Deleted","success")
        else:
            flash("Invalid API Key","error")
    return redirect(url_for('settings_apikeys_page'))

@app.route('/settings/initialSetup', methods=['POST'])
def initialSetup():
    firstRunCheck = check_existing_users()

    if firstRunCheck is False:
        username = request.form['username']
        email = request.form['email']
        password1 = request.form['password1']
        password2 = request.form['password2']
        serverName = request.form['serverName']
        serverAddress = request.form['serverAddress']
        smtpSendAs = request.form['smtpSendAs']
        smtpAddress = request.form['smtpAddress']
        smtpPort = request.form['smtpPort']
        smtpUser = request.form['smtpUser']
        smtpPassword = request.form['smtpPassword']

        recordSelect = False
        registerSelect = False
        emailValidationSelect = False
        adaptiveStreaming = False
        showEmptyTables = False
        allowComments = False
        smtpTLS = False
        smtpSSL = False

        if 'recordSelect' in request.form:
            recordSelect = True

        if 'registerSelect' in request.form:
            registerSelect = True

        if 'emailValidationSelect' in request.form:
            emailValidationSelect = True

        if 'adaptiveStreaming' in request.form:
            adaptiveStreaming = True

        if 'showEmptyTables' in request.form:
            showEmptyTables = True

        if 'allowComments' in request.form:
            allowComments = True

        if 'smtpTLS' in request.form:
            smtpTLS = True

        if 'smtpSSL' in request.form:
            smtpSSL = True


        if password1 == password2:

            passwordhash = utils.hash_password(password1)

            user_datastore.create_user(email=email, username=username, password=passwordhash)
            db.session.commit()
            user = Sec.User.query.filter_by(username=username).first()
            user_datastore.add_role_to_user(user,'Admin')
            user_datastore.add_role_to_user(user, 'Streamer')

            serverSettings = settings.settings(serverName, serverAddress, smtpAddress, smtpPort, smtpTLS, smtpSSL, smtpUser, smtpPassword, smtpSendAs, registerSelect, emailValidationSelect, recordSelect, adaptiveStreaming, showEmptyTables, allowComments, version)
            db.session.add(serverSettings)
            db.session.commit()

            sysSettings = settings.settings.query.first()

            if settings != None:
                app.config.update(
                    SERVER_NAME=None,
                    SECURITY_EMAIL_SENDER=sysSettings.smtpSendAs,
                    MAIL_SERVER=sysSettings.smtpAddress,
                    MAIL_PORT=sysSettings.smtpPort,
                    MAIL_USE_TLS=sysSettings.smtpTLS,
                    MAIL_USE_SSL=sysSettings.smtpSSL,
                    MAIL_USERNAME=sysSettings.smtpUsername,
                    MAIL_PASSWORD=sysSettings.smtpPassword,
                    SECURITY_REGISTERABLE=sysSettings.allowRegistration,
                    SECURITY_CONFIRMABLE = sysSettings.requireConfirmedEmail,
                    SECURITY_SEND_REGISTER_EMAIL = sysSettings.requireConfirmedEmail,
                    SECURITY_EMAIL_SUBJECT_PASSWORD_RESET = sysSettings.siteName + " - Password Reset Request",
                    SECURITY_EMAIL_SUBJECT_REGISTER = sysSettings.siteName + " - Welcome!",
                    SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE = sysSettings.siteName + " - Password Reset Notification",
                    SECURITY_EMAIL_SUBJECT_CONFIRM = sysSettings.siteName + " - Email Confirmation Request",
                    SECURITY_FORGOT_PASSWORD_TEMPLATE = 'themes/' + sysSettings.systemTheme + '/security/forgot_password.html',
                    SECURITY_LOGIN_USER_TEMPLATE = 'themes/' + sysSettings.systemTheme + '/security/login_user.html',
                    SECURITY_REGISTER_USER_TEMPLATE = 'themes/' + sysSettings.systemTheme + '/security/register_user.html',
                    SECURITY_RESET_PASSWORD_TEMPLATE = 'themes/' + sysSettings.systemTheme + '/security/reset_password.html',
                    SECURITY_SEND_CONFIRMATION_TEMPLATE = 'themes/'  + sysSettings.systemTheme + '/security/send_confirmation.html')
                global mail
                mail = Mail(app)

        else:
            flash('Passwords do not match')
            return redirect(url_for('main_page'))

    return redirect(url_for('main_page'))

### Start Video / Stream Handler Routes

@app.route('/videos/<string:channelID>/<path:filename>')
def video_sender(channelID, filename):
    channelQuery = Channel.Channel.query.filter_by(channelLoc=channelID).first()
    if channelQuery.protected:
        if check_isValidChannelViewer(channelQuery.id):
            redirect_path = "/osp-videos/" + str(channelID) + "/" + filename
            response = make_response("")
            response.headers["X-Accel-Redirect"] = redirect_path
            return response
        else:
            return abort(401)
    else:
        redirect_path = "/osp-videos/" + str(channelID) + "/" + filename
        response = make_response("")
        response.headers["X-Accel-Redirect"] = redirect_path
        return response

@app.route('/stream-thumb/<path:filename>')
def live_thumb_sender(filename):
    channelID = str(filename)[:-4]
    channelQuery = Channel.Channel.query.filter_by(channelLoc=channelID).first()
    if channelQuery.protected:
        if check_isValidChannelViewer(channelQuery.id):
            redirect_path = "/osp-streamthumbs" + "/" + filename
            response = make_response("")
            response.headers["X-Accel-Redirect"] = redirect_path
            return response
        else:
            return abort(401)
    else:
        redirect_path = "/osp-streamthumbs" + "/" + filename
        response = make_response("")
        response.headers["X-Accel-Redirect"] = redirect_path
        return response

@app.route('/live-adapt/<path:filename>')
def live_adapt_stream_image_sender(filename):
    channelID = str(filename)[:-5]
    channelQuery = Channel.Channel.query.filter_by(channelLoc=channelID).first()
    if channelQuery.protected:
        if check_isValidChannelViewer(channelQuery.id):
            redirect_path = "/osp-liveadapt" + "/" + filename
            response = make_response("")
            response.headers["X-Accel-Redirect"] = redirect_path
            return response
        else:
            return abort(401)
    else:
        redirect_path = "/osp-liveadapt" + "/" + filename
        response = make_response("")
        response.headers["X-Accel-Redirect"] = redirect_path
        return response

@app.route('/live-adapt/<string:channelID>/<path:filename>')
def live_adapt_stream_directory_sender(channelID, filename):
    channelQuery = Channel.Channel.query.filter_by(channelLoc=channelID[:-4]).first()
    if channelQuery.protected:
        if check_isValidChannelViewer(channelQuery.id):
            redirect_path = "/osp-liveadapt" + "/" + str(channelID) + "/" + filename
            response = make_response("")
            response.headers["X-Accel-Redirect"] = redirect_path
            return response
        else:
            return abort(401)
    else:
        redirect_path = "/osp-liveadapt" + "/" + str(channelID) + "/" + filename
        response = make_response("")
        response.headers["X-Accel-Redirect"] = redirect_path
        return response

@app.route('/live/<string:channelID>/<path:filename>')
def live_stream_directory_sender(channelID, filename):
    channelQuery = Channel.Channel.query.filter_by(channelLoc=channelID).first()
    if channelQuery.protected:
        if check_isValidChannelViewer(channelQuery.id):
            redirect_path = "/osp-live" + "/" + str(channelID) + "/" + filename
            response = make_response("")
            response.headers["X-Accel-Redirect"] = redirect_path
            return response

        else:
            return abort(401)
    else:
        redirect_path = "/osp-live" + "/" + str(channelID) + "/" + filename
        response = make_response("")
        response.headers["X-Accel-Redirect"] = redirect_path
        return response

@app.route('/live-rec/<string:channelID>/<path:filename>')
def live_rec_stream_directory_sender(channelID, filename):
    channelQuery = Channel.Channel.query.filter_by(channelLoc=channelID).first()
    if channelQuery.protected:
        if check_isValidChannelViewer(channelQuery.id):
            redirect_path = "/osp-liverec" + "/" + str(channelID) + "/" + filename
            response = make_response("")
            response.headers["X-Accel-Redirect"] = redirect_path
            return response
        else:
            abort(401)
    else:
        redirect_path = "/osp-liverec" + "/" + str(channelID) + "/" + filename
        response = make_response("")
        response.headers["X-Accel-Redirect"] = redirect_path
        return response

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
        if userQuery != None:
            if userQuery.has_role('Streamer'):

                if userQuery.active == False:
                    returnMessage = {'time': str(currentTime), 'status': 'Unauthorized User - User has been Disabled', 'key': str(key), 'ipAddress': str(ipaddress)}
                    print(returnMessage)
                    return abort(400)

                returnMessage = {'time': str(currentTime), 'status': 'Successful Key Auth', 'key': str(key), 'channelName': str(channelRequest.channelName), 'userName': str(channelRequest.owningUser), 'ipAddress': str(ipaddress)}
                print(returnMessage)

                validAddress = formatSiteAddress(sysSettings.siteAddress)

                externalIP = socket.gethostbyname(validAddress)
                existingStreamQuery = Stream.Stream.query.filter_by(linkedChannel=channelRequest.id).all()
                if existingStreamQuery != []:
                    for stream in existingStreamQuery:
                        db.session.delete(stream)
                    db.session.commit()

                newStream = Stream.Stream(key, normalize_date(str(currentTime)), int(channelRequest.id), channelRequest.topic)
                db.session.add(newStream)
                db.session.commit()

                if channelRequest.record is False:
                    if sysSettings.adaptiveStreaming == True:
                        return redirect('rtmp://' + externalIP + '/stream-data-adapt/' + channelRequest.channelLoc, code=302)
                    else:
                        return redirect('rtmp://' + externalIP + '/stream-data/' + channelRequest.channelLoc, code=302)
                elif channelRequest.record is True:

                    userCheck = Sec.User.query.filter_by(id=channelRequest.owningUser).first()
                    existingRecordingQuery = RecordedVideo.RecordedVideo.query.filter_by(channelID=channelRequest.id, pending=True).all()
                    if existingRecordingQuery != []:
                        for recording in existingRecordingQuery:
                            db.session.delete(recording)
                            db.session.commit()

                    newRecording = RecordedVideo.RecordedVideo(userCheck.id, channelRequest.id, channelRequest.channelName, channelRequest.topic, 0, "", currentTime, channelRequest.allowComments)
                    db.session.add(newRecording)
                    db.session.commit()
                    if sysSettings.adaptiveStreaming == True:
                        return redirect('rtmp://' + externalIP + '/streamrec-data-adapt/' + channelRequest.channelLoc, code=302)
                    else:
                        return redirect('rtmp://' + externalIP + '/streamrec-data/' + channelRequest.channelLoc, code=302)
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
    global streamUserList

    key = request.form['name']
    ipaddress = request.form['addr']

    requestedChannel = Channel.Channel.query.filter_by(channelLoc=key).first()

    authedStream = Stream.Stream.query.filter_by(streamKey=requestedChannel.streamKey).first()

    if authedStream is not None:
        returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Successful Channel Auth', 'key': str(requestedChannel.streamKey), 'channelName': str(requestedChannel.channelName), 'ipAddress': str(ipaddress)}
        print(returnMessage)
        streamUserList[authedStream.id] = []

        if requestedChannel.imageLocation is None:
            channelImage = (sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
        else:
            channelImage = (sysSettings.siteAddress + "/images/" + requestedChannel.imageLocation)

        runWebhook(requestedChannel.id, 0, channelname=requestedChannel.channelName, channelurl=(sysSettings.siteAddress + "/channel/" + str(requestedChannel.id)), channeltopic=requestedChannel.topic,
                   channelimage=channelImage, streamer=get_userName(requestedChannel.owningUser), channeldescription=requestedChannel.description,
                   streamname=authedStream.streamName, streamurl=(sysSettings.siteAddress + "/view/" + requestedChannel.channelLoc), streamtopic=get_topicName(authedStream.topic), streamimage=(sysSettings.siteAddress + "/stream-thumb/" + requestedChannel.channelLoc + ".png"))
        return 'OK'
    else:
        returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Failed Channel Auth. No Authorized Stream Key', 'channelName': str(key), 'ipAddress': str(ipaddress)}
        print(returnMessage)
        db.session.close()
        return abort(400)


@app.route('/deauth-user', methods=['POST'])
def user_deauth_check():
    sysSettings = settings.settings.query.first()
    global streamUserList

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

            returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Stream Closed', 'key': str(key), 'channelName': str(channelRequest.channelName), 'userName':str(channelRequest.owningUser), 'ipAddress': str(ipaddress)}
            streamUserList[channelRequest.channelLoc] = []
            print(returnMessage)

            if channelRequest.imageLocation is None:
                channelImage = (sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
            else:
                channelImage = (sysSettings.siteAddress + "/images/" + channelRequest.imageLocation)

            runWebhook(channelRequest.id, 1, channelname=channelRequest.channelName,
                       channelurl=(sysSettings.siteAddress + "/channel/" + str(channelRequest.id)),
                       channeltopic=channelRequest.topic,
                       channelimage=channelImage, streamer=get_userName(channelRequest.owningUser),
                       channeldescription=channelRequest.description,
                       streamname=stream.streamName,
                       streamurl=(sysSettings.siteAddress + "/view/" + channelRequest.channelLoc),
                       streamtopic=get_topicName(stream.topic),
                       streamimage=(sysSettings.siteAddress + "/stream-thumb/" + channelRequest.channelLoc + ".png"))
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
    videoPath = videoPath.replace('.flv','.mp4')

    pendingVideo.thumbnailLocation = imagePath
    pendingVideo.videoLocation = videoPath

    fullVidPath = '/var/www/videos/' + videoPath

    pendingVideo.pending = False
    db.session.commit()

    if requestedChannel.imageLocation is None:
        channelImage = (sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
    else:
        channelImage = (sysSettings.siteAddress + "/images/" + requestedChannel.imageLocation)

    runWebhook(requestedChannel.id, 6, channelname=requestedChannel.channelName,
               channelurl=(sysSettings.siteAddress + "/channel/" + str(requestedChannel.id)),
               channeltopic=get_topicName(requestedChannel.topic),
               channelimage=channelImage, streamer=get_userName(requestedChannel.owningUser),
               channeldescription=requestedChannel.description, videoname=pendingVideo.channelName,
               videodate=pendingVideo.videoDate, videodescription=pendingVideo.description,videotopic=get_topicName(pendingVideo.topic),
               videourl=(sysSettings.siteAddress + '/play/' + str(pendingVideo.id)),
               videothumbnail=(sysSettings.siteAddress + '/videos/' + pendingVideo.thumbnailLocation))

    while not os.path.exists(fullVidPath):
        time.sleep(1)

    if os.path.isfile(fullVidPath):
        pendingVideo.length = getVidLength(fullVidPath)
        db.session.commit()

    db.session.close()
    return 'OK'



### Start Socket.IO Functions ###

@socketio.on('newViewer')
def handle_new_viewer(streamData):
    channelLoc = str(streamData['data'])

    sysSettings = settings.settings.query.first()
    global streamUserList

    requestedChannel = Channel.Channel.query.filter_by(channelLoc=channelLoc).first()
    stream = Stream.Stream.query.filter_by(streamKey=requestedChannel.streamKey).first()

    streamName = ""
    streamTopic = 0

    requestedChannel.currentViewers = requestedChannel.currentViewers + 1

    if stream is not None:
        stream.currentViewers = stream.currentViewers + 1
        db.session.commit()
        streamName = stream.streamName
        streamTopic = stream.topic
    else:
        streamName = requestedChannel.channelName
        streamTopic = requestedChannel.topic

    if requestedChannel.imageLocation is None:
        channelImage = (sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
    else:
        channelImage = (sysSettings.siteAddress + "/images/" + requestedChannel.imageLocation)

    join_room(streamData['data'])

    if current_user.is_authenticated:
        pictureLocation = current_user.pictureLocation
        if current_user.pictureLocation == None:
            pictureLocation = '/static/img/user2.png'
        else:
            pictureLocation = '/images/' + pictureLocation

        if current_user.username not in streamUserList[channelLoc]:
            streamUserList[channelLoc].append(current_user.username)
        emit('message', {'user':'Server','msg': current_user.username + ' has entered the room.', 'image': pictureLocation}, room=streamData['data'])
        runWebhook(requestedChannel.id, 2, channelname=requestedChannel.channelName,
                   channelurl=(sysSettings.siteAddress + "/channel/" + str(requestedChannel.id)),
                   channeltopic=requestedChannel.topic,
                   channelimage=channelImage, streamer=get_userName(requestedChannel.owningUser),
                   channeldescription=requestedChannel.description,
                   streamname=streamName,
                   streamurl=(sysSettings.siteAddress + "/view/" + requestedChannel.channelLoc),
                   streamtopic=get_topicName(streamTopic),
                   streamimage=(sysSettings.siteAddress + "/stream-thumb/" + requestedChannel.channelLoc + ".png"),
                   user=current_user.username, userpicture=(sysSettings.siteAddress + pictureLocation))
        db.session.commit()
        db.session.close()
    else:
        emit('message', {'user':'Server','msg': 'Guest has entered the room.', 'image': '/static/img/user2.png'}, room=streamData['data'])
        runWebhook(requestedChannel.id, 2, channelname=requestedChannel.channelName,
                   channelurl=(sysSettings.siteAddress + "/channel/" + str(requestedChannel.id)),
                   channeltopic=requestedChannel.topic,
                   channelimage=channelImage, streamer=get_userName(requestedChannel.owningUser),
                   channeldescription=requestedChannel.description,
                   streamname=streamName,
                   streamurl=(sysSettings.siteAddress + "/view/" + requestedChannel.channelLoc),
                   streamtopic=get_topicName(streamTopic),
                   streamimage=(sysSettings.siteAddress + "/stream-thumb/" + requestedChannel.channelLoc + ".png"),
                   user="Guest", userpicture=(sysSettings.siteAddress + '/static/img/user2.png'))
        db.session.commit()
        db.session.close()

@socketio.on('openPopup')
def handle_new_popup_viewer(streamData):
    join_room(streamData['data'])

@socketio.on('removeViewer')
def handle_leaving_viewer(streamData):
    channelLoc = str(streamData['data'])

    global streamUserList

    requestedChannel = Channel.Channel.query.filter_by(channelLoc=channelLoc).first()
    stream = Stream.Stream.query.filter_by(streamKey=requestedChannel.streamKey).first()

    requestedChannel.currentViewers = requestedChannel.currentViewers - 1
    if requestedChannel.currentViewers < 0:
        requestedChannel.currentViewers = 0
    db.session.commit()

    if stream is not None:
        stream.currentViewers = stream.currentViewers - 1
        if stream.currentViewers < 0:
            stream.currentViewers = 0
        db.session.commit()
    leave_room(streamData['data'])
    if current_user.is_authenticated:

        pictureLocation = current_user.pictureLocation
        if current_user.pictureLocation == None:
            pictureLocation = '/static/img/user2.png'
        else:
            pictureLocation = '/images/' + pictureLocation

        if current_user.username in streamUserList[channelLoc]:
            streamUserList[channelLoc].remove(current_user.username)
        emit('message', {'user':'Server', 'msg': current_user.username + ' has left the room.', 'image': pictureLocation}, room=streamData['data'])
        db.session.commit()
        db.session.close()
    else:
        emit('message', {'user':'Server', 'msg': 'Guest has left the room.', 'image': '/static/img/user2.png'}, room=streamData['data'])
        db.session.commit()
        db.session.close()

@socketio.on('closePopup')
def handle_leaving_popup_viewer(streamData):
    leave_room(streamData['data'])

@socketio.on('getViewerTotal')
def handle_viewer_total_request(streamData):
    channelLoc = str(streamData['data'])
    global streamUserList

    requestedChannel = Channel.Channel.query.filter_by(channelLoc=channelLoc).first()

    viewers = requestedChannel.currentViewers

    db.session.commit()
    db.session.close()
    emit('viewerTotalResponse', {'data': str(viewers), 'userList': streamUserList[channelLoc]})

@socketio.on('getUpvoteTotal')
def handle_upvote_total_request(streamData):
    loc = streamData['loc']
    vidType = str(streamData['vidType'])

    myUpvote = False
    totalUpvotes = 0

    totalQuery = None
    myVoteQuery = None

    if vidType == 'stream':
        loc = str(loc)
        channelQuery = Channel.Channel.query.filter_by(channelLoc=loc).first()
        if channelQuery.stream != []:
            stream = channelQuery.stream[0]
            totalQuery = upvotes.streamUpvotes.query.filter_by(streamID=stream.id).all()
            try:
                myVoteQuery = upvotes.streamUpvotes.query.filter_by(userID=current_user.id, streamID=stream.id).first()
            except:
                pass

    elif vidType == 'video':
        loc = int(loc)
        totalQuery = upvotes.videoUpvotes.query.filter_by(videoID=loc).all()
        try:
            myVoteQuery = upvotes.videoUpvotes.query.filter_by(userID=current_user.id, videoID=loc).first()
        except:
            pass
    elif vidType == "comment":
        loc = int(loc)
        totalQuery = upvotes.commentUpvotes.query.filter_by(commentID=loc).all()
        try:
            myVoteQuery = upvotes.commentUpvotes.query.filter_by(userID=current_user.id, commentID=loc).first()
        except:
            pass

    if totalQuery != None:
        for vote in totalQuery:
            totalUpvotes = totalUpvotes + 1
    if myVoteQuery != None:
        myUpvote = True

    db.session.commit()
    db.session.close()
    emit('upvoteTotalResponse', {'totalUpvotes': str(totalUpvotes), 'myUpvote': str(myUpvote), 'type': vidType, 'loc': loc})

@socketio.on('changeUpvote')
def handle_upvoteChange(streamData):
    loc = streamData['loc']
    vidType = str(streamData['vidType'])

    if vidType == 'stream':
        loc = str(loc)
        channelQuery = Channel.Channel.query.filter_by(channelLoc=loc).first()
        if channelQuery.stream != []:
            stream = channelQuery.stream[0]
            myVoteQuery = upvotes.streamUpvotes.query.filter_by(userID=current_user.id, streamID=stream.id).first()

            if myVoteQuery == None:
                newUpvote = upvotes.streamUpvotes(current_user.id, stream.id)
                db.session.add(newUpvote)
            else:
                db.session.delete(myVoteQuery)
            db.session.commit()

    elif vidType == 'video':
        loc = int(loc)
        myVoteQuery = upvotes.videoUpvotes.query.filter_by(userID=current_user.id, videoID=loc).first()

        if myVoteQuery == None:
            newUpvote = upvotes.videoUpvotes(current_user.id, loc)
            db.session.add(newUpvote)
        else:
            db.session.delete(myVoteQuery)
        db.session.commit()
    elif vidType == "comment":
        loc = int(loc)
        videoCommentQuery = comments.videoComments.query.filter_by(id=loc).first()
        if videoCommentQuery != None:
            myVoteQuery = upvotes.commentUpvotes.query.filter_by(userID=current_user.id, commentID=videoCommentQuery.id).first()
            if myVoteQuery == None:
                newUpvote = upvotes.commentUpvotes(current_user.id, videoCommentQuery.id)
                db.session.add(newUpvote)
            else:
                db.session.delete(myVoteQuery)
            db.session.commit()
    db.session.close()



@socketio.on('disconnect')
def disconnect(message):
    logger.error(message)
    emit('message', {'msg': message['msg']})

@socketio.on('setScreenShot')
def setScreenShot(message):
    video = message['loc']
    timeStamp = message['timeStamp']

    if video != None:
        videoQuery = RecordedVideo.RecordedVideo.query.filter_by(id=int(video)).first()
        if videoQuery != None and videoQuery.owningUser == current_user.id:
            videoLocation = '/var/www/videos/' + videoQuery.videoLocation
            thumbnailLocation = '/var/www/videos/' + videoQuery.thumbnailLocation
            db.session.close()
            try:
                os.remove(thumbnailLocation)
            except OSError:
                pass
            result = subprocess.call(['ffmpeg', '-ss', str(timeStamp), '-i', videoLocation, '-s', '384x216', '-vframes', '1', thumbnailLocation])

@socketio.on('updateStreamData')
def updateStreamData(message):
    channelLoc = message['channel']

    sysSettings = settings.settings.query.first()

    channelQuery = Channel.Channel.query.filter_by(channelLoc=channelLoc, owningUser=current_user.id).first()

    if channelQuery != None:
        stream = channelQuery.stream[0]
        stream.streamName = strip_html(message['name'])
        stream.topic = int(message['topic'])
        db.session.commit()

        if channelQuery.imageLocation is None:
            channelImage = (sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
        else:
            channelImage = (sysSettings.siteAddress + "/images/" + channelQuery.imageLocation)

        runWebhook(channelQuery.id, 4, channelname=channelQuery.channelName,
                   channelurl=(sysSettings.siteAddress + "/channel/" + str(channelQuery.id)),
                   channeltopic=channelQuery.topic,
                   channelimage=channelImage, streamer=get_userName(channelQuery.owningUser),
                   channeldescription=channelQuery.description,
                   streamname=stream.streamName,
                   streamurl=(sysSettings.siteAddress + "/view/" + channelQuery.channelLoc),
                   streamtopic=get_topicName(stream.topic),
                   streamimage=(sysSettings.siteAddress + "/stream-thumb/" + channelQuery.channelLoc + ".png"))
        db.session.commit()
        db.session.close()
@socketio.on('newScreenShot')
def newScreenShot(message):
    video = message['loc']
    timeStamp = message['timeStamp']

    if video != None:
        videoQuery = RecordedVideo.RecordedVideo.query.filter_by(id=int(video)).first()
        if videoQuery != None and videoQuery.owningUser == current_user.id:
            videoLocation = '/var/www/videos/' + videoQuery.videoLocation
            thumbnailLocation = '/var/www/videos/' + videoQuery.channel.channelLoc + '/tempThumbnail.png'
            try:
                os.remove(thumbnailLocation)
            except OSError:
                pass
            result = subprocess.call(['ffmpeg', '-ss', str(timeStamp), '-i', videoLocation, '-s', '384x216', '-vframes', '1', thumbnailLocation])
            tempLocation = '/videos/' + videoQuery.channel.channelLoc + '/tempThumbnail.png?dummy=' + str(random.randint(1,50000))
            emit('checkScreenShot', {'thumbnailLocation': tempLocation, 'timestamp':timeStamp}, broadcast=False)
            db.session.close()

@socketio.on('text')
def text(message):
    """Sent by a client when the user entered a new message.
    The message is sent to all people in the room."""
    room = message['room']
    msg = strip_html(message['msg'])

    sysSettings = settings.settings.query.first()

    channelQuery = Channel.Channel.query.filter_by(channelLoc=room).first()

    if channelQuery != None:

        pictureLocation = current_user.pictureLocation
        if current_user.pictureLocation == None:
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
            elif msg.startswith('/mute'):
                if (current_user.has_role('Admin')) or (current_user.id == channelQuery.owningUser):
                    channelQuery.channelMuted = True
                    db.session.commit()
                    msg = "<b> *** " + current_user.username + " has muted the chat channel ***"
                    emit('message', {'user': current_user.username, 'image': pictureLocation, 'msg': msg}, room=room)
                    return
            elif msg.startswith('/unmute'):
                if (current_user.has_role('Admin')) or (current_user.id == channelQuery.owningUser):
                    channelQuery.channelMuted = False
                    db.session.commit()
                    msg = "<b> *** " + current_user.username + " has unmuted the chat channel ***"
                    emit('message', {'user': current_user.username, 'image': pictureLocation, 'msg': msg}, room=room)
                    return
            elif msg.startswith('/ban '):
                if (current_user.has_role('Admin')) or (current_user.id == channelQuery.owningUser):
                    commandArray = msg.split(' ', 1)
                    if len(commandArray) >= 2:
                        command = commandArray[0]
                        target = commandArray[1]

                        userQuery = Sec.User.query.filter_by(username=target).first()

                        if userQuery != None:
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

                        if userQuery != None:
                            banQuery = banList.banList.query.filter_by(userID=userQuery.id, channelLoc=room).first()
                            if banQuery != None:
                                db.session.delete(banQuery)
                                db.session.commit()

                                msg = '<b>*** ' + target + ' has been unbanned ***</b>'

        banQuery = banList.banList.query.filter_by(userID=current_user.id, channelLoc=room).first()

        if banQuery == None:
            if channelQuery.channelMuted == False or channelQuery.owningUser == current_user.id:
                flags = ""
                if current_user.id == channelQuery.owningUser:
                    flags = "Owner"

                if channelQuery.imageLocation is None:
                    channelImage = (sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
                else:
                    channelImage = (sysSettings.siteAddress + "/images/" + channelQuery.imageLocation)

                streamName = None
                streamTopic = None

                if channelQuery.stream != []:
                    streamName = channelQuery.stream[0].streamName
                    streamTopic = channelQuery.stream[0].topic
                else:
                    streamName = channelQuery.channelName
                    streamTopic = channelQuery.topic

                runWebhook(channelQuery.id, 5, channelname=channelQuery.channelName,
                           channelurl=(sysSettings.siteAddress + "/channel/" + str(channelQuery.id)),
                           channeltopic=get_topicName(channelQuery.topic),
                           channelimage=channelImage, streamer=get_userName(channelQuery.owningUser),
                           channeldescription=channelQuery.description,
                           streamname=streamName,
                           streamurl=(sysSettings.siteAddress + "/view/" + channelQuery.channelLoc),
                           streamtopic=get_topicName(streamTopic), streamimage=(sysSettings.siteAddress + "/stream-thumb/" + channelQuery.channelLoc + ".png"),
                           user=current_user.username, userpicture=sysSettings.siteAddress + pictureLocation, message=msg)
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


@socketio.on('getServerResources')
def get_resource_usage(message):
    cpuUsage = psutil.cpu_percent(interval=1)
    memoryUsage = psutil.virtual_memory()[2]
    diskUsage = psutil.disk_usage('/')[3]

    emit('serverResources', {'cpuUsage':cpuUsage,'memoryUsage':memoryUsage, 'diskUsage':diskUsage})

@socketio.on('generateInviteCode')
def generateInviteCode(message):
    daysToExpire = int(message['daysToExpiration'])
    channelID = int(message['chanID'])

    channelQuery = Channel.Channel.query.filter_by(id=channelID, owningUser=current_user.id).first()

    if channelQuery is not None:
        newInviteCode = invites.inviteCode(daysToExpire, channelID)
        db.session.add(newInviteCode)
        db.session.commit()

        emit('newInviteCode', {'code': str(newInviteCode.code), 'expiration': str(newInviteCode.expiration), 'channelID':str(newInviteCode.channelID)}, broadcast=False)

    else:
        #emit('newInviteCode', {'code': 'error', 'expiration': 'error', 'channelID': channelID}, broadcast=False)
        pass
    db.session.close()

@socketio.on('deleteInviteCode')
def deleteInviteCode(message):
    code = message['code']
    codeQuery = invites.inviteCode.query.filter_by(code=code).first()
    channelQuery = Channel.Channel.query.filter_by(id=codeQuery.channelID).first()
    if codeQuery is not None:
        if (channelQuery.owningUser is current_user.id) or (current_user.has_role('Admin')):
            channelID = channelQuery.id
            db.session.delete(codeQuery)
            db.session.commit()
            emit('inviteCodeDeleteAck', {'code': str(code), 'channelID': str(channelID)}, broadcast=False)
        else:
            emit('inviteCodeDeleteFail', {'code': 'fail', 'channelID': 'fail'}, broadcast=False)
    else:
        emit('inviteCodeDeleteFail', {'code': 'fail', 'channelID': 'fail'}, broadcast=False)

    db.session.close()

@socketio.on('addUserChannelInvite')
def addUserChannelInvite(message):
    channelID = int(message['chanID'])
    username = message['username']
    daysToExpire = message['daysToExpiration']

    channelQuery = Channel.Channel.query.filter_by(id=channelID, owningUser=current_user.id).first()

    if channelQuery != None:
        invitedUserQuery = Sec.User.query.filter(func.lower(Sec.User.username) == func.lower(username)).first()
        if invitedUserQuery is not None:
            previouslyInvited = False
            for invite in invitedUserQuery.invites:
                if invite.channelID is not channelID:
                    previouslyInvited = True

            if not previouslyInvited:
                newUserInvite = invites.invitedViewer(invitedUserQuery.id, channelID, daysToExpire)
                db.session.add(newUserInvite)
                db.session.commit()

                emit('invitedUserAck', {'username': username, 'added': str(newUserInvite.addedDate), 'expiration': str(newUserInvite.expiration), 'channelID': str(channelID), 'id': str(newUserInvite.id)}, broadcast=False)
                db.session.commit()
                db.session.close()
    db.session.close()

@socketio.on('deleteInvitedUser')
def deleteInvitedUser(message):
    inviteID = int(message['inviteID'])
    inviteIDQuery = invites.invitedViewer.query.filter_by(id=inviteID).first()
    channelQuery = Channel.Channel.query.filter_by(id=inviteIDQuery.channelID).first()
    if inviteIDQuery != None:
        if (channelQuery.owningUser is current_user.id) or (current_user.has_role('Admin')):
            db.session.delete(inviteIDQuery)
            db.session.commit()
            emit('invitedUserDeleteAck', {'inviteID': str(inviteID)}, broadcast=False)
    db.session.close()

@socketio.on('checkUniqueUsername')
def deleteInvitedUser(message):
    newUsername = message['username']
    userQuery = Sec.User.query.filter(func.lower(Sec.User.username) == func.lower(newUsername)).first()
    if userQuery is None:
        emit('checkUniqueUsernameAck', {'results': str(1)}, broadcast=False)
    else:
        emit('checkUniqueUsernameAck', {'results': str(0)}, broadcast=False)
    db.session.commit()
    db.session.close()


@socketio.on('submitWebhook')
def addChangeWebhook(message):
    channelID = int(message['webhookChannelID'])

    channelQuery = Channel.Channel.query.filter_by(id=channelID, owningUser=current_user.id).first()
    if channelQuery is not None:
        webhookName = message['webhookName']
        webhookEndpoint = message['webhookEndpoint']
        webhookTrigger = int(message['webhookTrigger'])
        webhookHeader = message['webhookHeader']
        webhookPayload = message['webhookPayload']
        webhookReqType = int(message['webhookReqType'])
        webhookInputAction = message['inputAction']
        webhookInputID = message['webhookInputID']


        if webhookInputAction == 'new':
            newWebHook = webhook.webhook(webhookName, channelID, webhookEndpoint, webhookHeader, webhookPayload, webhookReqType, webhookTrigger)
            db.session.add(newWebHook)
            db.session.commit()
            emit('newWebhookAck', {'webhookName': webhookName, 'requestURL':webhookEndpoint, 'requestHeader':webhookHeader, 'requestPayload':webhookPayload, 'requestType':webhookReqType, 'requestTrigger':webhookTrigger, 'requestID':newWebHook.id, 'channelID':channelID}, broadcast=False)
        elif webhookInputAction == 'edit':
            existingWebhookQuery = webhook.webhook.query.filter_by(channelID=channelID, id=int(webhookInputID)).first()
            if existingWebhookQuery is not None:
                existingWebhookQuery.name = webhookName
                existingWebhookQuery.endpointURL = webhookEndpoint
                existingWebhookQuery.requestHeader = webhookHeader
                existingWebhookQuery.requestPayload = webhookPayload
                existingWebhookQuery.requestType = webhookReqType
                existingWebhookQuery.requestTrigger = webhookTrigger


                emit('changeWebhookAck', {'webhookName': webhookName, 'requestURL': webhookEndpoint, 'requestHeader': webhookHeader, 'requestPayload': webhookPayload, 'requestType': webhookReqType, 'requestTrigger': webhookTrigger, 'requestID': existingWebhookQuery.id, 'channelID': channelID}, broadcast=False)
    db.session.commit()
    db.session.close()

@socketio.on('deleteWebhook')
def deleteWebhook(message):
    webhookID = int(message['webhookID'])
    webhookQuery = webhook.webhook.query.filter_by(id=webhookID).first()

    if webhookQuery is not None:
        channelQuery = webhookQuery.channel
        if channelQuery is not None:
            if channelQuery.owningUser is current_user.id:
                db.session.delete(webhookQuery)
                db.session.commit()
    db.session.close()

# Start App Initiation
try:
    init_db_values()

except Exception as e:
    print(e)
mail = Mail(app)

if __name__ == '__main__':
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    socketio.run(app)
