# -*- coding: UTF-8 -*-
from gevent import monkey
monkey.patch_all(thread=True)

import git

from flask import Flask, redirect, request, abort, render_template, url_for, flash, send_from_directory, make_response, Response, session
from flask_security import Security, SQLAlchemyUserDatastore, login_required, current_user, roles_required
from flask_security.utils import hash_password
from flask_security.signals import user_registered, confirm_instructions_sent
from flask_security import utils
from sqlalchemy.sql.expression import func
from sqlalchemy import desc, asc
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class
from flask_mail import Mail, Message
from flask_migrate import Migrate, migrate, upgrade
from flaskext.markdown import Markdown
import xmltodict
from werkzeug.contrib.fixers import ProxyFix
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis

from apscheduler.schedulers.background import BackgroundScheduler

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
import hashlib
from urllib.parse import urlparse

import smtplib

#Import Paths
cwp = sys.path[0]
sys.path.append(cwp)
sys.path.append('./classes')


from html.parser import HTMLParser

import logging

import datetime

from conf import config

#----------------------------------------------------------------------------#
# App Configuration Setup
#----------------------------------------------------------------------------#

version = "beta-4"

# TODO Move Hubsite URL to System Configuration.  Only here for testing/dev of Hub
hubURL = "https://hub.openstreamingplatform.com"

app = Flask(__name__)

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
app.config['SECURITY_REGISTERABLE'] = config.allowRegistration
app.config['SECURITY_RECOVERABLE'] = True
app.config['SECURITY_CONFIRMABLE'] = config.requireEmailRegistration
app.config['SECURITY_SEND_REGISTER_EMAIL'] = config.requireEmailRegistration
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
app.config['VIDEO_UPLOAD_TEMPFOLDER'] = '/var/www/videos/temp'
app.config["VIDEO_UPLOAD_EXTENSIONS"] = ["PNG", "MP4"]

logger = logging.getLogger('gunicorn.error').handlers

# Init Redis DB and Clear Existing DB
r = redis.Redis(host='localhost', port=6379)
r.flushdb()

appDBVersion = 0.45

from classes.shared import db

from classes.shared import socketio
socketio.init_app(app, logger=False, engineio_logger=False, message_queue='redis://')

limiter = Limiter(app, key_func=get_remote_address)

db.init_app(app)
db.app = app
migrateObj = Migrate(app, db)

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
#from classes import hubConnection
from classes import logs
from classes import subscriptions

sysSettings = None

#Register APIv1 Blueprint
app.register_blueprint(api_v1)

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, Sec.User, Sec.Role)
security = Security(app, user_datastore, register_form=Sec.ExtendedRegisterForm, confirm_register_form=Sec.ExtendedConfirmRegisterForm)

# Setup Flask-Uploads
photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)
patch_request_class(app)

#Initialize Flask-Markdown
md = Markdown(app, extensions=['tables'])

# Establish Channel SID List
#streamSIDList = {}

# Create Theme Data Dictionary
themeData = {}

#----------------------------------------------------------------------------#
# Functions
#----------------------------------------------------------------------------#
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
        if sysSettings.systemTheme == None or sysSettings.systemTheme == "Default":
            sysSettings.systemTheme = "Defaultv2"
            db.session.commit()
        if sysSettings.siteProtocol == None:
            sysSettings.siteProtocol = "http://"
            db.session.commit()
        if sysSettings.version == "None":
            sysSettings.version = version
            db.session.commit()
        if sysSettings.systemLogo == None:
            sysSettings.systemLogo = "/static/img/logo.png"
            db.session.commit()
        # Sets allowComments to False if None is Set - Usual Cause is moving from Alpha to Beta
        if sysSettings.allowComments == None:
            sysSettings.allowComments = False
            db.session.commit()
        # Sets allowUploads to False if None is Set - Caused by Moving from Pre-Beta 2
        if sysSettings.allowUploads == None:
            sysSettings.allowUploads = False
            db.session.commit()
        # Sets Blank Server Message to Prevent Crash if set to None
        if sysSettings.serverMessage == None:
            sysSettings.serverMessage = ""
            db.session.commit()
        # Checks Channel Settings and Corrects Missing Fields - Usual Cause is moving from Older Versions to Newer
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
        channelQuery = Channel.Channel.query.filter_by(showChatJoinLeaveNotification=None).all()
        for chan in channelQuery:
            chan.showChatJoinLeaveNotification = True
            db.session.commit()
        channelQuery = Channel.Channel.query.filter_by(currentViewers=None).all()
        for chan in channelQuery:
            chan.currentViewers = 0
            db.session.commit()
        channelQuery = Channel.Channel.query.filter_by(defaultStreamName=None).all()
        for chan in channelQuery:
            chan.defaultStreamName = ""
            db.session.commit()

        #hubQuery = hubConnection.hubServers.query.filter_by(serverAddress=hubURL).first()
        #if hubQuery == None:
        #    newHub = hubConnection.hubServers(hubURL)
        #    db.session.add(newHub)
        #    db.session.commit()

        # Create the stream-thumb directory if it does not exist
        if not os.path.isdir("/var/www/stream-thumb"):
            try:
                os.mkdir("/var/www/stream-thumb")
            except OSError:
                flash("Unable to create /var/www/stream-thumb", "error")

        sysSettings = settings.settings.query.first()

        app.config['SERVER_NAME'] = None
        app.config['SECURITY_EMAIL_SENDER'] = sysSettings.smtpSendAs
        app.config['MAIL_DEFAULT_SENDER'] = sysSettings.smtpSendAs
        app.config['MAIL_SERVER'] = sysSettings.smtpAddress
        app.config['MAIL_PORT'] = sysSettings.smtpPort
        app.config['MAIL_USE_SSL'] = sysSettings.smtpSSL
        app.config['MAIL_USE_TLS'] = sysSettings.smtpTLS
        app.config['MAIL_USERNAME'] = sysSettings.smtpUsername
        app.config['MAIL_PASSWORD'] = sysSettings.smtpPassword
        app.config['SECURITY_FORGOT_PASSWORD_TEMPLATE'] = 'themes/' + sysSettings.systemTheme + '/security/forgot_password.html'
        app.config['SECURITY_LOGIN_USER_TEMPLATE'] = 'themes/' + sysSettings.systemTheme + '/security/login_user.html'
        app.config['SECURITY_REGISTER_USER_TEMPLATE'] = 'themes/' + sysSettings.systemTheme + '/security/register_user.html'
        app.config['SECURITY_SEND_CONFIRMATION_TEMPLATE'] = 'themes/' + sysSettings.systemTheme + '/security/send_confirmation.html'
        app.config['SECURITY_RESET_PASSWORD_TEMPLATE'] = 'themes/' + sysSettings.systemTheme + '/security/reset_password.html'
        app.config['SECURITY_EMAIL_SUBJECT_PASSWORD_RESET'] = sysSettings.siteName + " - Password Reset Request"
        app.config['SECURITY_EMAIL_SUBJECT_REGISTER'] = sysSettings.siteName + " - Welcome!"
        app.config['SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE'] = sysSettings.siteName + " - Password Reset Notification"
        app.config['SECURITY_EMAIL_SUBJECT_CONFIRM'] = sysSettings.siteName + " - Email Confirmation Request"

        # Import Theme Data into Theme Dictionary
        with open('templates/themes/' + sysSettings.systemTheme +'/theme.json') as f:
            global themeData

            themeData = json.load(f)

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

def newLog(logType, message):
    newLogItem = logs.logs(datetime.datetime.now(), str(message), logType)
    db.session.add(newLogItem)
    db.session.commit()
    return True

def check_existing_users():
    existingUserQuery = Sec.User.query.all()

    if existingUserQuery == []:
        return False
    else:
        return True

# Class Required for HTML Stripping in strip_html
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

# Checks Length of a Video at path and returns the length
def getVidLength(input_video):
    result = subprocess.check_output(['ffprobe', '-i', input_video, '-show_entries', 'format=duration', '-loglevel', '8', '-of', 'csv=%s' % ("p=0")])
    return float(result)

def get_Video_Upvotes(videoID):
    videoUpVotesQuery = upvotes.videoUpvotes.query.filter_by(videoID=videoID).count()
    result = videoUpVotesQuery
    return result

def get_Stream_Upvotes(videoID):
    videoUpVotesQuery = upvotes.streamUpvotes.query.filter_by(streamID=videoID).count()
    result = videoUpVotesQuery
    return result

def get_Clip_Upvotes(videoID):
    videoUpVotesQuery = upvotes.clipUpvotes.query.filter_by(clipID=videoID).count()
    result = videoUpVotesQuery
    return result

def get_Video_Comments(videoID):
    videoCommentsQuery = comments.videoComments.query.filter_by(videoID=videoID).count()
    result = videoCommentsQuery
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
    if current_user.is_authenticated:
        commentQuery = upvotes.commentUpvotes.query.filter_by(commentID=int(commentID), userID=current_user.id).first()
        if commentQuery != None:
            return True
        else:
            return False
    return False

def check_isUserValidRTMPViewer(userID,channelID):
    userQuery = Sec.User.query.filter_by(id=userID).first()
    if userQuery is not None:
        channelQuery = Channel.Channel.query.filter_by(id=channelID).first()
        if channelQuery is not None:
            if channelQuery.owningUser is userQuery.id:
                return True
            else:
                inviteQuery = invites.invitedViewer.query.filter_by(userID=userQuery.id, channelID=channelID).all()
                for invite in inviteQuery:
                    if invite.isValid():
                        return True
                    else:
                        db.session.delete(invite)
                        db.session.commit()
    return False

def table2Dict(table):
    exportedTableList = table.query.all()
    dataList = []
    for tbl in exportedTableList:
        dataList.append(dict((column.name, str(getattr(tbl, column.name))) for column in tbl.__table__.columns))
    return dataList

def videoupload_allowedExt(filename):
    if not "." in filename:
        return False
    ext = filename.rsplit(".", 1)[1]
    if ext.upper() in app.config["VIDEO_UPLOAD_EXTENSIONS"]:
        return True
    else:
        return False

# Checks Theme Override Data and if does not exist in override, use Defaultv2's HTML with theme's layout.html
def checkOverride(themeHTMLFile):
    if themeHTMLFile in themeData['Override']:
        sysSettings = db.session.query(settings.settings).first()
        return "themes/" + sysSettings.systemTheme + "/" + themeHTMLFile
    else:
        return "themes/Defaultv2/" + themeHTMLFile

def sendTestEmail(smtpServer, smtpPort, smtpTLS, smtpSSL, smtpUsername, smtpPassword, smtpSender, smtpReceiver):
    server = None
    sslContext = None
    if smtpSSL is True:
        import ssl
        sslContext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)

    server = smtplib.SMTP(smtpServer, int(smtpPort))
    try:
        if smtpTLS or smtpSSL:
            server.ehlo()
            if smtpSSL:
                server.starttls(context=sslContext)
            else:
                server.starttls()
            server.ehlo()
        if smtpUsername and smtpPassword:
            server.login(smtpUsername, smtpPassword)
        msg = "Test Email - Your Instance of OSP has been successfully configured!"
        server.sendmail(smtpSender, smtpReceiver, msg)
    except Exception as e:
        print(e)
        newLog(1, "Test Email Failed for " + str(smtpServer) + "Reason:" + str(e))
        return False
    server.quit()
    newLog(1, "Test Email Successful for " + str(smtpServer))
    return True

@asynch
def runWebhook(channelID, triggerType, **kwargs):
    webhookQueue = []
    if channelID != "ZZZ":

        webhookQuery = webhook.webhook.query.filter_by(channelID=channelID, requestTrigger=triggerType).all()
        webhookQueue.append(webhookQuery)

    globalWebhookQuery = webhook.globalWebhook.query.filter_by(requestTrigger=triggerType).all()
    webhookQueue.append(globalWebhookQuery)

    for queue in webhookQueue:
        if queue != []:
            for hook in queue:
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
                newLog(8, "Processing Webhook for ID #" + str(hook.id) + " - Destination:" + str(url))
    db.session.commit()
    db.session.close()

def processWebhookVariables(payload, **kwargs):
    for key, value in kwargs.items():
        replacementValue = ("%" + key + "%")
        payload = payload.replace(replacementValue, str(value))
    return payload

@asynch
def runSubscriptions(channelID, subject, message):
    sysSettings = settings.settings.query.first()
    subscriptionQuery = subscriptions.channelSubs.query.filter_by(channelID=channelID).all()
    with mail.connect() as conn:
        for sub in subscriptionQuery:
            userQuery = Sec.User.query.filter_by(id=int(sub.userID)).first()
            if userQuery != None:
                finalMessage = message + "<p>If you would like to unsubscribe, click the link below: <br><a href='" + sysSettings.siteProtocol + sysSettings.siteAddress + "/unsubscribe?email=" + userQuery.email + "'>Unsubscribe</a></p></body></html>"
                msg = Message(subject, recipients=[userQuery.email])
                msg.sender = sysSettings.siteName + "<" + sysSettings.smtpSendAs + ">"
                msg.body = finalMessage
                msg.html = finalMessage
                conn.send(msg)
    return True

def processSubscriptions(channelID, subject, message):
    subscriptionQuery = subscriptions.channelSubs.query.filter_by(channelID=channelID).all()
    if subscriptionQuery != []:
        newLog(2, "Sending Subscription Emails for Channel ID: " + str(channelID))
        try:
            runSubscriptions(channelID, subject, message)
        except:
            newLog(0, "Subscriptions Failed due to possible misconfiguration")
    return True

def prepareHubJSON():
    topicQuery = topics.topics.query.all()
    topicDump = {}
    for topic in topicQuery:
        topicDump[topic.id] = {"name": topic.name, "img": topic.iconClass}

    streamerIDs = []
    for channel in db.session.query(Channel.Channel.owningUser).distinct():
        if channel.owningUser not in streamerIDs:
            streamerIDs.append(channel.owningUser)

    streamerDump = {}
    for streamerID in streamerIDs:
        streamerQuery = Sec.User.query.filter_by(id=streamerID).first()
        streamerDump[streamerQuery.id] = {"username": streamerQuery.username, "biography": streamerQuery.biography,
                                          "img": streamerQuery.pictureLocation, "location": "/streamers/" + str(streamerQuery.id) + "/"}

    channelDump = {}
    channelQuery = Channel.Channel.query.all()
    for channel in channelQuery:
        channelDump[channel.id] = {"streamer": channel.owningUser, "name": channel.channelName,
                                   "location": "/channel/link/" + channel.channelLoc, "topic": channel.topic, "views": channel.views,
                                   "protected": channel.protected,
                                   "currentViewers": channel.currentViewers, "img": channel.imageLocation,
                                   "description": channel.description}

    videoDump = {}
    videoQuery = RecordedVideo.RecordedVideo.query.filter_by(pending=False).all()
    for video in videoQuery:
        videoDump[video.id] = {"streamer": video.owningUser, "name": video.channelName, "channelID": video.channelID,
                               "description": video.description, "topic": video.topic, "views": video.views,
                               "length": video.length, "location": "/play/" + str(video.id), "img": video.thumbnailLocation, "upvotes": str(get_Video_Upvotes(video.id))}

    clipDump = {}
    clipQuery = RecordedVideo.Clips.query.all()
    for clip in clipQuery:
        clipDump[clip.id] = {"parentVideo": clip.parentVideo, "length": clip.length, "views": clip.views,
                             "name": clip.clipName, "description": clip.description, "img": clip.thumbnailLocation, "location": "/clip/" + str(clip.id), "upvotes": str(get_Clip_Upvotes(clip.id))}

    streamDump = {}
    streamQuery = Stream.Stream.query.all()
    for stream in streamQuery:
        streamDump[stream.id] = {"channelID": stream.linkedChannel, "location": ("/view/" + stream.channel.channelLoc + "/"), "streamer": str(stream.channel.owningUser),
                                 "name": stream.streamName, "topic": stream.topic, "currentViewers": stream.currentViewers, "views": stream.totalViewers,
                                 "img": stream.channel.channelLoc + ".png", "upvotes": str(get_Stream_Upvotes(stream.id))}

    dataDump = {"topics": topicDump, "streamers": streamerDump, "channels": channelDump, "videos": videoDump,
                "clips": clipDump, "streams": streamDump}
    db.session.close()
    return dataDump

def processHubConnection(connection, payload):
    hubServer = connection.server
    apiEndpoint = "apiv1"

    r = None
    try:
        r = requests.post(hubServer.serverAddress + '/' + apiEndpoint + '/update', data={'serverToken': connection.serverToken, 'jsonData': json.dumps(payload)})
    except requests.exceptions.Timeout:
        newLog(10, "Failed Update to OSP Hub Due to Timeout - Server:" + str(hubServer.serverAddress))
        return False
    except requests.exceptions.ConnectionError:
        newLog(10, "Failed Update to OSP Hub Due to Connection Error - Server:" + str(hubServer.serverAddress))
        return False
    if r.status_code == 200:
        connection.lastUpload = datetime.datetime.now()
        db.session.commit()
        db.session.close()
        newLog(10,"Successful Update to OSP Hub - Server:" + str(hubServer.serverAddress))
        return True
    else:
        newLog(10, "Failed Update to OSP Hub Due to Error " + str(r.status_code) + " - Server:" + str(hubServer.serverAddress))
    return False

#def processAllHubConnections():
#    jsonPayload = prepareHubJSON()
#
#    results = []
#
#    hubConnectionQuery = hubConnection.hubConnection.query.filter_by(status=1).all()
#    for connection in hubConnectionQuery:
#        results.append(processHubConnection(connection, jsonPayload))
#    return results

app.jinja_env.globals.update(check_isValidChannelViewer=check_isValidChannelViewer)
app.jinja_env.globals.update(check_isCommentUpvoted=check_isCommentUpvoted)

#----------------------------------------------------------------------------#
# Scheduler Tasks
#----------------------------------------------------------------------------#

scheduler = BackgroundScheduler()
#scheduler.add_job(func=processAllHubConnections, trigger="interval", seconds=180)
scheduler.start()

#----------------------------------------------------------------------------#
# Context Processors
#----------------------------------------------------------------------------#

@app.context_processor
def inject_user_info():
    return dict(user=current_user)


@app.context_processor
def inject_sysSettings():
    db.session.commit()
    sysSettings = db.session.query(settings.settings).first()

    return dict(sysSettings=sysSettings)

#----------------------------------------------------------------------------#
# Template Filters
#----------------------------------------------------------------------------#

@app.template_filter('normalize_uuid')
def normalize_uuid(uuidstr):
    return uuidstr.replace("-", "")

@app.template_filter('normalize_urlroot')
def normalize_urlroot(urlString):
    parsedURLRoot = urlparse(urlString)
    URLProtocol = None
    if parsedURLRoot.port == 80:
        URLProtocol = "http"
    elif parsedURLRoot.port == 443:
        URLProtocol = "https"
    else:
        URLProtocol = parsedURLRoot.scheme
    reparsedString = str(URLProtocol) + "://" + str(parsedURLRoot.hostname)
    return str(reparsedString)

@app.template_filter('normalize_url')
def normalize_url(urlString):
    parsedURL = urlparse(urlString)
    if parsedURL.port == 80:
        URLProtocol = "http"
    elif parsedURL.port == 443:
        URLProtocol = "https"
    else:
        URLProtocol = parsedURL.scheme
    reparsedString = str(URLProtocol) + "://" + str(parsedURL.hostname) + str(parsedURL.path)
    return str(reparsedString)

@app.template_filter('normalize_date')
def normalize_date(dateStr):
    return str(dateStr)[:19]

@app.template_filter('limit_title')
def limit_title(titleStr):
    if len(titleStr) > 40:
        return titleStr[:37] + "..."
    else:
        return titleStr

@app.template_filter('format_kbps')
def format_kbps(bits):
    bits = int(bits)
    return round(bits/1000)

@app.template_filter('hms_format')
def hms_format(seconds):
    val = "Unknown"
    if seconds != None:
        seconds = int(seconds)
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

@app.template_filter('get_Clip_Upvotes')
def get_Clip_Upvotes_Filter(videoID):
    result = get_Clip_Upvotes(videoID)
    return result

@app.template_filter('get_Video_Comments')
def get_Video_Comments_Filter(videoID):
    result = get_Video_Comments(videoID)
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

@ app.template_filter('testList')
def testList(obj):
    if type(obj) == list:
        return True
    else:
        return False

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
        '9': 'Video Name Change',
        '10': 'Channel Subscription',
        '20': 'New User'
    }
    return webhookNames[webhookTrigger]

@app.template_filter('get_hubStatus')
def get_hubStatus(hubStatus):

    hubStatus = str(hubStatus)
    hubStatusNames = {
        '0': 'Unverified',
        '1': 'Verified'
    }
    return hubStatusNames[hubStatus]

#@app.template_filter('get_hubName')
#def get_hubName(hubID):
#
#    hubID = int(hubID)
#    hubQuery = hubConnection.hubServers.query.filter_by(id=hubID).first()
#    if hubQuery != None:
#        return hubQuery.serverAddress
#    return "Unknown"

@app.template_filter('get_logType')
def get_logType(logType):

    logType = str(logType)
    logTypeNames = {
        '0': 'System',
        '1': 'Security',
        '2': 'Email',
        '3': 'Channel',
        '4': 'Video',
        '5': 'Stream',
        '6': 'Clip',
        '7': 'API',
        '8': 'Webhook',
        '9': 'Topic',
        '10': 'Hub'
    }
    return logTypeNames[logType]

#----------------------------------------------------------------------------#
# Flask Signal Handlers.
#----------------------------------------------------------------------------#

@user_registered.connect_via(app)
def user_registered_sighandler(app, user, confirm_token):
    default_role = user_datastore.find_role("User")
    user_datastore.add_role_to_user(user, default_role)
    runWebhook("ZZZ", 20, user=user.username)
    newLog(1, "A New User has Registered - Username:" + str(user.username))
    if config.requireEmailRegistration == True:
        flash("An email has been sent to the email provided. Please check your email and verify your account to activate.")
    db.session.commit()

#----------------------------------------------------------------------------#
# Error Handlers.
#----------------------------------------------------------------------------#
@app.errorhandler(404)
def page_not_found(e):
    sysSettings = settings.settings.query.first()
    newLog(0, "404 Error - " + str(request.url))
    return render_template(checkOverride('404.html'), sysSetting=sysSettings), 404

@app.errorhandler(500)
def page_not_found(e):
    sysSettings = settings.settings.query.first()
    newLog(0,"500 Error - " + str(request.url))
    return render_template(checkOverride('500.html'), sysSetting=sysSettings, error=e), 500

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

    firstRunCheck = check_existing_users()

    if firstRunCheck is False:
        return render_template('/firstrun.html')

    else:
        sysSettings = settings.settings.query.first()
        activeStreams = Stream.Stream.query.order_by(Stream.Stream.currentViewers).all()

        randomRecorded = RecordedVideo.RecordedVideo.query.filter_by(pending=False).order_by(func.random()).limit(16)

        randomClips = RecordedVideo.Clips.query.order_by(func.random()).limit(16)

        return render_template(checkOverride('index.html'), streamList=activeStreams, randomRecorded=randomRecorded, randomClips=randomClips)

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
    return render_template(checkOverride('channels.html'), channelList=channelList)

@app.route('/channel/<int:chanID>/')
def channel_view_page(chanID):
    sysSettings = settings.settings.query.first()
    chanID = int(chanID)
    channelData = Channel.Channel.query.filter_by(id=chanID).first()

    if channelData != None:

        openStreams = Stream.Stream.query.filter_by(linkedChannel=chanID).all()
        recordedVids = RecordedVideo.RecordedVideo.query.filter_by(channelID=chanID, pending=False).all()

        # Sort Video to Show Newest First
        recordedVids.sort(key=lambda x: x.videoDate, reverse=True)

        clipsList = []
        for vid in recordedVids:
            for clip in vid.clips:
                clipsList.append(clip)

        clipsList.sort(key=lambda x: x.views, reverse=True)

        subState = False
        if current_user.is_authenticated:
            chanSubQuery = subscriptions.channelSubs.query.filter_by(channelID=channelData.id, userID=current_user.id).first()
            if chanSubQuery is not None:
                subState = True

        return render_template(checkOverride('videoListView.html'), channelData=channelData, openStreams=openStreams, recordedVids=recordedVids, clipsList=clipsList, subState=subState, title="Channels - Videos")
    else:
        flash("No Such Channel", "error")
        return redirect(url_for("main_page"))

@app.route('/channel/link/<channelLoc>/')
def channel_view_link_page(channelLoc):
    if channelLoc != None:
        channelQuery = Channel.Channel.query.filter_by(channelLoc=str(channelLoc)).first()
        if channelQuery != None:
            return redirect(url_for("channel_view_page",chanID=channelQuery.id))
    flash("Invalid Channel Location", "error")
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

    topicsList.sort(key=lambda x: x.name)

    return render_template(checkOverride('topics.html'), topicsList=topicsList)


@app.route('/topic/<topicID>/')
def topic_view_page(topicID):
    sysSettings = settings.settings.query.first()
    topicID = int(topicID)
    streamsQuery = Stream.Stream.query.filter_by(topic=topicID).all()
    recordedVideoQuery = RecordedVideo.RecordedVideo.query.filter_by(topic=topicID, pending=False).all()

    # Sort Video to Show Newest First
    recordedVideoQuery.sort(key=lambda x: x.videoDate, reverse=True)

    clipsList = []
    for vid in recordedVideoQuery:
        for clip in vid.clips:
            clipsList.append(clip)

    clipsList.sort(key=lambda x: x.views, reverse=True)

    return render_template(checkOverride('videoListView.html'), openStreams=streamsQuery, recordedVids=recordedVideoQuery, clipsList=clipsList, title="Topics - Videos")

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

    return render_template(checkOverride('streamers.html'), streamerList=streamerList)

@app.route('/streamers/<userID>/')
def streamers_view_page(userID):
    sysSettings = settings.settings.query.first()
    userID = int(userID)

    streamerQuery = Sec.User.query.filter_by(id=userID).first()
    if streamerQuery != None:
        if streamerQuery.has_role('Streamer'):
            userChannels = Channel.Channel.query.filter_by(owningUser=userID).all()

            streams = []

            for channel in userChannels:
                for stream in channel.stream:
                    streams.append(stream)

            recordedVideoQuery = RecordedVideo.RecordedVideo.query.filter_by(owningUser=userID, pending=False).all()

            # Sort Video to Show Newest First
            recordedVideoQuery.sort(key=lambda x: x.videoDate, reverse=True)

            clipsList = []
            for vid in recordedVideoQuery:
                for clip in vid.clips:
                    clipsList.append(clip)

            clipsList.sort(key=lambda x: x.views, reverse=True)

            return render_template(checkOverride('videoListView.html'), openStreams=streams, recordedVids=recordedVideoQuery, userChannels=userChannels, clipsList=clipsList, title=streamerQuery.username, streamerData=streamerQuery)
    flash('Invalid Streamer','error')
    return redirect(url_for("main_page"))


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
            return render_template(checkOverride('channelProtectionAuth.html'))

    #global streamUserList

    #if requestedChannel.channelLoc not in streamUserList:
    #    streamUserList[requestedChannel.channelLoc] = []

    #global streamSIDList

    #if requestedChannel.channelLoc not in streamSIDList:
    #    streamSIDList[requestedChannel.channelLoc] = []

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
                hideBar = False

                hideBarReq = request.args.get("hideBar")
                if hideBarReq == "True" or hideBarReq == "true":
                    hideBar = True

                return render_template(checkOverride('chatpopout.html'), stream=streamData, streamURL=streamURL, sysSettings=sysSettings, channel=requestedChannel, hideBar=hideBar)
            else:
                flash("Chat is Not Enabled For This Stream","error")

        isEmbedded = request.args.get("embedded")

        newView = views.views(0, requestedChannel.id)
        db.session.add(newView)
        db.session.commit()

        if isEmbedded == None or isEmbedded == "False":

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

            randomRecorded = RecordedVideo.RecordedVideo.query.filter_by(pending=False, channelID=requestedChannel.id).order_by(func.random()).limit(16)

            clipsList = []
            for vid in requestedChannel.recordedVideo:
                for clip in vid.clips:
                    clipsList.append(clip)
            clipsList.sort(key=lambda x: x.views, reverse=True)

            subState = False
            if current_user.is_authenticated:
                chanSubQuery = subscriptions.channelSubs.query.filter_by(channelID=requestedChannel.id, userID=current_user.id).first()
                if chanSubQuery is not None:
                    subState = True

            return render_template(checkOverride('channelplayer.html'), stream=streamData, streamURL=streamURL, topics=topicList, randomRecorded=randomRecorded, channel=requestedChannel, clipsList=clipsList,
                                   subState=subState, secureHash=secureHash, rtmpURI=rtmpURI)
        else:
            isAutoPlay = request.args.get("autoplay")
            if isAutoPlay == None:
                isAutoPlay = False
            elif isAutoPlay.lower() == 'true':
                isAutoPlay = True
            else:
                isAutoPlay = False
            return render_template(checkOverride('player_embed.html'), stream=streamData, streamURL=streamURL, topics=topicList, isAutoPlay=isAutoPlay)

    else:
        flash("No Live Stream at URL","error")
        return redirect(url_for("main_page"))


@app.route('/play/<videoID>')
def view_vid_page(videoID):
    sysSettings = settings.settings.query.first()

    recordedVid = RecordedVideo.RecordedVideo.query.filter_by(id=videoID).first()

    if recordedVid != None:

        if recordedVid.channel.protected:
            if not check_isValidChannelViewer(recordedVid.channel.id):
                return render_template(checkOverride('channelProtectionAuth.html'))

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

        # Function to allow custom start time on Video
        startTime = None
        if 'startTime' in request.args:
            startTime = request.args.get("startTime")
        try:
            startTime = float(startTime)
        except:
            startTime = None

        if isEmbedded == None or isEmbedded == "False":

            randomRecorded = RecordedVideo.RecordedVideo.query.filter(RecordedVideo.RecordedVideo.pending == False, RecordedVideo.RecordedVideo.id != recordedVid.id).order_by(func.random()).limit(12)

            subState = False
            if current_user.is_authenticated:
                chanSubQuery = subscriptions.channelSubs.query.filter_by(channelID=recordedVid.channel.id, userID=current_user.id).first()
                if chanSubQuery is not None:
                    subState = True

            return render_template(checkOverride('vidplayer.html'), video=recordedVid, streamURL=streamURL, topics=topicList, randomRecorded=randomRecorded, subState=subState, startTime=startTime)
        else:
            isAutoPlay = request.args.get("autoplay")
            if isAutoPlay == None:
                isAutoPlay = False
            elif isAutoPlay.lower() == 'true':
                isAutoPlay = True
            else:
                isAutoPlay = False
            return render_template(checkOverride('vidplayer_embed.html'), video=recordedVid, streamURL=streamURL, topics=topicList, isAutoPlay=isAutoPlay, startTime=startTime)
    else:
        flash("No Such Video at URL","error")
        return redirect(url_for("main_page"))

@app.route('/play/<loc>/clip', methods=['POST'])
@login_required
def vid_clip_page(loc):
    # TODO Add Webhook for Clip Creation
    recordedVidQuery = RecordedVideo.RecordedVideo.query.filter_by(id=int(loc), owningUser=current_user.id).first()
    sysSettings = settings.settings.query.first()

    if recordedVidQuery != None:
        clipStart = float(request.form['clipStartTime'])
        clipStop = float(request.form['clipStopTime'])
        clipName = str(request.form['clipName'])
        clipDescription = str(request.form['clipDescription'])

        if clipStop > clipStart:
            newClip = RecordedVideo.Clips(recordedVidQuery.id, clipStart, clipStop, clipName, clipDescription)
            db.session.add(newClip)
            db.session.commit()

            newClipQuery = RecordedVideo.Clips.query.filter_by(id=newClip.id).first()

            videoLocation = '/var/www/videos/' + recordedVidQuery.videoLocation
            clipThumbNailLocation = recordedVidQuery.channel.channelLoc + '/clips/' + 'clip-' + str(newClipQuery.id) + ".png"

            newClipQuery.thumbnailLocation = clipThumbNailLocation

            fullthumbnailLocation = '/var/www/videos/' + clipThumbNailLocation

            if not os.path.isdir("/var/www/videos/" + recordedVidQuery.channel.channelLoc + '/clips'):
                os.mkdir("/var/www/videos/" + recordedVidQuery.channel.channelLoc + '/clips')

            result = subprocess.call(['ffmpeg', '-ss', str(clipStart), '-i', videoLocation, '-s', '384x216', '-vframes', '1', fullthumbnailLocation])

            redirectID = newClipQuery.id
            newLog(6, "New Clip Created - ID #" + str(redirectID))
            db.session.commit()
            db.session.close()
            flash("Clip Created", "success")

            return redirect(url_for("view_clip_page", clipID=redirectID))
        else:
            flash("Invalid Start/Stop Time for Clip", "error")
    flash("Invalid Video ID", "error")
    return redirect(url_for("view_vid_page", videoID=loc))

@app.route('/play/<loc>/move', methods=['POST'])
@login_required
def vid_move_page(loc):
    recordedVidQuery = RecordedVideo.RecordedVideo.query.filter_by(id=int(loc), owningUser=current_user.id).first()
    sysSettings = settings.settings.query.first()

    if recordedVidQuery != None:
        newChannel = int(request.form['moveToChannelID'])
        newChannelQuery = Channel.Channel.query.filter_by(id=newChannel, owningUser=current_user.id).first()
        if newChannelQuery != None:
            recordedVidQuery.channelID = newChannelQuery.id
            coreVideo = (recordedVidQuery.videoLocation.split("/")[1]).split("_", 1)[1]
            if not os.path.isdir("/var/www/videos/" + newChannelQuery.channelLoc):
                try:
                    os.mkdir("/var/www/videos/" + newChannelQuery.channelLoc)
                except OSError:
                    newLog(4, "Error Moving Video ID #" + str(recordedVidQuery.id) + "to Channel ID" + str(newChannelQuery.id) + "/" + newChannelQuery.channelLoc)
                    flash("Error Moving Video - Unable to Create Directory","error")
                    return redirect(url_for("main_page"))
            shutil.move("/var/www/videos/" + recordedVidQuery.videoLocation, "/var/www/videos/" + newChannelQuery.channelLoc + "/" + newChannelQuery.channelLoc + "_" + coreVideo)
            recordedVidQuery.videoLocation = newChannelQuery.channelLoc + "/" + newChannelQuery.channelLoc + "_" + coreVideo
            if (recordedVidQuery.thumbnailLocation != None) and (os.path.exists("/var/www/videos/" + recordedVidQuery.thumbnailLocation)):
                coreThumbnail = (recordedVidQuery.thumbnailLocation.split("/")[1]).split("_", 1)[1]
                shutil.move("/var/www/videos/" + recordedVidQuery.thumbnailLocation,"/var/www/videos/" + newChannelQuery.channelLoc + "/" + newChannelQuery.channelLoc + "_" + coreThumbnail)
                recordedVidQuery.thumbnailLocation = newChannelQuery.channelLoc + "/" + newChannelQuery.channelLoc + "_" + coreThumbnail
            for clip in recordedVidQuery.clips:
                coreThumbnail = (clip.thumbnailLocation.split("/")[2])
                if not os.path.isdir("/var/www/videos/" + newChannelQuery.channelLoc + '/clips'):
                    try:
                        os.mkdir("/var/www/videos/" + newChannelQuery.channelLoc + '/clips')
                    except OSError:
                        newLog(4, "Error Moving Video ID #" + str(recordedVidQuery.id) + "to Channel ID" + str(newChannelQuery.id) + "/" + newChannelQuery.channelLoc)
                        flash("Error Moving Video - Unable to Create Clips Directory", "error")
                        return redirect(url_for("main_page"))
                newClipLocation = "/var/www/videos/" + newChannelQuery.channelLoc +"/clips/" + coreThumbnail
                shutil.move("/var/www/videos/" + clip.thumbnailLocation, newClipLocation)
                clip.thumbnailLocation = newChannelQuery.channelLoc +"/clips/" + coreThumbnail

            db.session.commit()
            newLog(4, "Video ID #" + str(recordedVidQuery.id) + "Moved to Channel ID" + str(newChannelQuery.id) + "/" + newChannelQuery.channelLoc)
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
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
            else:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + recordedVidQuery.channel.imageLocation)

            runWebhook(recordedVidQuery.channel.id, 9, channelname=recordedVidQuery.channel.channelName,
                       channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(recordedVidQuery.channel.id)),
                       channeltopic=get_topicName(recordedVidQuery.channel.topic),
                       channelimage=channelImage, streamer=get_userName(recordedVidQuery.channel.owningUser),
                       channeldescription=recordedVidQuery.channel.description, videoname=recordedVidQuery.channelName,
                       videodate=recordedVidQuery.videoDate, videodescription=recordedVidQuery.description,
                       videotopic=get_topicName(recordedVidQuery.topic),
                       videourl=(sysSettings.siteProtocol + sysSettings.siteAddress + '/videos/' + recordedVidQuery.videoLocation),
                       videothumbnail=(sysSettings.siteProtocol + sysSettings.siteAddress + '/videos/' + recordedVidQuery.thumbnailLocation))
            db.session.commit()
            newLog(4, "Video Metadata Changed - ID # " + str(recordedVidQuery.id))

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

        # Delete Clips Attached to Video
        for clip in recordedVid.clips:
            thumbnailPath = '/var/www/videos/' + clip.thumbnailLocation

            if thumbnailPath != '/var/www/videos/':
                if os.path.exists(thumbnailPath) and (clip.thumbnailLocation != None or clip.thumbnailLocation != ""):
                    os.remove(thumbnailPath)
            db.session.delete(clip)

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
        flash("Video deleted")
        newLog(4, "Video Deleted - ID #" + str(videoID))
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
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
            else:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + recordedVid.channel.imageLocation)

            pictureLocation = ""
            if current_user.pictureLocation == None:
                pictureLocation = '/static/img/user2.png'
            else:
                pictureLocation = '/images/' + pictureLocation

            runWebhook(recordedVid.channel.id, 7, channelname=recordedVid.channel.channelName,
                       channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(recordedVid.channel.id)),
                       channeltopic=get_topicName(recordedVid.channel.topic),
                       channelimage=channelImage, streamer=get_userName(recordedVid.channel.owningUser),
                       channeldescription=recordedVid.channel.description, videoname=recordedVid.channelName,
                       videodate=recordedVid.videoDate, videodescription=recordedVid.description,
                       videotopic=get_topicName(recordedVid.topic),
                       videourl=(sysSettings.siteProtocol +sysSettings.siteAddress + '/videos/' + recordedVid.videoLocation),
                       videothumbnail=(sysSettings.siteProtocol + sysSettings.siteAddress + '/videos/' + recordedVid.thumbnailLocation),
                       user=current_user.username, userpicture=(sysSettings.siteProtocol + sysSettings.siteAddress + pictureLocation), comment=comment)
            flash('Comment Added', "success")
            newLog(4, "Video Comment Added by " + current_user.username + "to Video ID #" + str(recordedVid.id))

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
                        newLog(4, "Video Comment Deleted by " + current_user.username + "to Video ID #" + str(recordedVid.id))
                        flash('Comment Deleted', "success")
                    else:
                        flash("Not Authorized to Remove Comment", "error")

    else:
        flash('Invalid Video ID','error')
        return redirect(url_for('main_page'))

    return redirect(url_for('view_vid_page', videoID=videoID))

@app.route('/clip/<clipID>')
def view_clip_page(clipID):
    sysSettings = settings.settings.query.first()

    clipQuery = RecordedVideo.Clips.query.filter_by(id=int(clipID)).first()

    if clipQuery != None:

        recordedVid = RecordedVideo.RecordedVideo.query.filter_by(id=clipQuery.recordedVideo.id).first()

        if recordedVid.channel.protected:
            if not check_isValidChannelViewer(clipQuery.recordedVideo.channel.id):
                return render_template(checkOverride('channelProtectionAuth.html'))

        if recordedVid != None:
            clipQuery.views = clipQuery.views + 1
            clipQuery.recordedVideo.channel.views = clipQuery.recordedVideo.channel.views + 1

            if recordedVid.length == None:
                fullVidPath = '/var/www/videos/' + recordedVid.videoLocation
                duration = getVidLength(fullVidPath)
                recordedVid.length = duration
            db.session.commit()

            topicList = topics.topics.query.all()

            streamURL = '/videos/' + recordedVid.videoLocation

            isEmbedded = request.args.get("embedded")

            if isEmbedded == None or isEmbedded == "False":

                randomClips = RecordedVideo.Clips.query.filter(RecordedVideo.Clips.id != clipQuery.id).order_by(func.random()).limit(12)

                subState = False
                if current_user.is_authenticated:
                    chanSubQuery = subscriptions.channelSubs.query.filter_by(channelID=recordedVid.channel.id, userID=current_user.id).first()
                    if chanSubQuery is not None:
                        subState = True

                return render_template(checkOverride('clipplayer.html'), video=recordedVid, streamURL=streamURL, topics=topicList, randomClips=randomClips, subState=subState, clip=clipQuery)
            #else:
            #    isAutoPlay = request.args.get("autoplay")
            #    if isAutoPlay == None:
            #        isAutoPlay = False
            #    elif isAutoPlay.lower() == 'true':
            #        isAutoPlay = True
            #    else:
            #        isAutoPlay = False
            #    return render_template(checkOverride('vidplayer_embed.html'), video=recordedVid, streamURL=streamURL, topics=topicList, isAutoPlay=isAutoPlay, startTime=startTime)
    else:
        flash("No Such Clip at URL","error")
        return redirect(url_for("main_page"))

@app.route('/clip/<clipID>/delete')
@login_required
def delete_clip_page(clipID):

    clipQuery = RecordedVideo.Clips.query.filter_by(id=int(clipID)).first()

    if current_user.id == clipQuery.recordedVideo.owningUser and clipQuery != None:
        thumbnailPath = '/var/www/videos/' + clipQuery.thumbnailLocation

        if thumbnailPath != '/var/www/videos/':
            if os.path.exists(thumbnailPath) and (thumbnailPath != None or thumbnailPath != ""):
                os.remove(thumbnailPath)

        db.session.delete(clipQuery)

        db.session.commit()
        newLog(6,"Clip Deleted - ID #" + str(clipID))
        flash("Clip deleted")
        return redirect(url_for('main_page'))
    else:
        flash("Error Deleting Clip")
        return redirect(url_for('view_clip_page', clipID=clipID))

@app.route('/clip/<clipID>/change', methods=['POST'])
@login_required
def clip_change_page(clipID):
    # TODO Add Webhook for Clip Metadata Change

    clipQuery = RecordedVideo.Clips.query.filter_by(id=int(clipID)).first()
    sysSettings = settings.settings.query.first()

    if clipQuery != None:
        if clipQuery.recordedVideo.owningUser == current_user.id:

            newClipName = request.form['newVidName']
            description = request.form['description']

            clipQuery.clipName = strip_html(newClipName)
            clipQuery.description = strip_html(description)

            db.session.commit()
            newLog(6, "Clip Metadata Changed - ID #" + str(clipID))
            return redirect(url_for('view_clip_page', clipID=clipID))

    flash("Error Changing Clip Metadata", "error")
    return redirect(url_for("main_page"))

@app.route('/upload/video-files', methods=['GET', 'POST'])
@login_required
@roles_required('Streamer')
def upload():
    sysSettings = settings.settings.query.first()
    if sysSettings.allowUploads == False:
        db.session.close()
        return ("Video Uploads Disabled", 501)
    if request.files['file']:

        if not os.path.exists('/var/www/videos/temp'):
            os.makedirs('/var/www/videos/temp')

        file = request.files['file']

        if request.form['ospfilename'] != "":
            ospfilename = request.form['ospfilename']
        else:
            return ("Ooops.", 500)

        if videoupload_allowedExt(file.filename):
            save_path = os.path.join(app.config['VIDEO_UPLOAD_TEMPFOLDER'], secure_filename(ospfilename))
            current_chunk = int(request.form['dzchunkindex'])
        else:
            newLog(4,"File Upload Failed - File Type not Allowed - Username:" + current_user.username)
            return ("Filetype not allowed", 403)

        if current_chunk > 4500:
            open(save_path, 'w').close()
            return ("File is getting too large.", 403)

        if os.path.exists(save_path) and current_chunk == 0:
            open(save_path, 'w').close()

        try:
            with open(save_path, 'ab') as f:
                f.seek(int(request.form['dzchunkbyteoffset']))
                f.write(file.stream.read())
        except OSError:
            newLog(4, "File Upload Failed - OSError - Username:" + current_user.username)
            return ("Ooops.", 500)

        total_chunks = int(request.form['dztotalchunkcount'])

        if current_chunk + 1 == total_chunks:
            if os.path.getsize(save_path) != int(request.form['dztotalfilesize']):
                return ("Size mismatch", 500)

        return ("success", 200)
    else:
        return ("I don't understand", 501)

@app.route('/upload/video-details', methods=['POST'])
@login_required
@roles_required('Streamer')
def upload_vid():
    sysSettings = settings.settings.query.first()
    if sysSettings.allowUploads == False:
        db.session.close()
        flash("Video Upload Disabled", "error")
        return redirect(url_for('main_page'))

    currentTime = datetime.datetime.now()

    channel = int(request.form['uploadToChannelID'])
    thumbnailFilename = request.form['thumbnailFilename']
    videoFilename= request.form['videoFilename']

    ChannelQuery = Channel.Channel.query.filter_by(id=channel).first()

    if ChannelQuery.owningUser != current_user.id:
        flash('You are not allowed to upload to this channel!')
        db.session.close()
        return redirect(url_for('main_page'))

    newVideo = RecordedVideo.RecordedVideo(current_user.id, channel, ChannelQuery.channelName, ChannelQuery.topic, 0, "", currentTime, ChannelQuery.allowComments)

    videoLoc = ChannelQuery.channelLoc + "/" + videoFilename.rsplit(".", 1)[0] + '_' + datetime.datetime.strftime(currentTime, '%Y%m%d_%H%M%S') + ".mp4"
    videoPath = '/var/www/videos/' + videoLoc

    if videoFilename != "":
        if not os.path.isdir("/var/www/videos/" + ChannelQuery.channelLoc):
            try:
                os.mkdir("/var/www/videos/" + ChannelQuery.channelLoc)
            except OSError:
                newLog(4, "File Upload Failed - OSError - Unable to Create Directory - Username:" + current_user.username)
                flash("Error uploading video - Unable to create directory","error")
                db.session.close()
                return redirect(url_for("main_page"))
        shutil.move(app.config['VIDEO_UPLOAD_TEMPFOLDER'] + '/' + videoFilename, videoPath)
    else:
        db.session.close()
        flash("Error uploading video - Couldn't move video file")
        return redirect(url_for('main_page'))

    newVideo.videoLocation = videoLoc

    if thumbnailFilename != "":
        thumbnailLoc = ChannelQuery.channelLoc + '/' + thumbnailFilename.rsplit(".", 1)[0] + '_' +  datetime.datetime.strftime(currentTime, '%Y%m%d_%H%M%S') + ".png"
        thumbnailPath = '/var/www/videos/' + thumbnailLoc
        shutil.move(app.config['VIDEO_UPLOAD_TEMPFOLDER'] + '/' + thumbnailFilename, thumbnailPath)
        newVideo.thumbnailLocation = thumbnailLoc
    else:
        thumbnailLoc = ChannelQuery.channelLoc + '/' + videoFilename.rsplit(".", 1)[0] + '_' +  datetime.datetime.strftime(currentTime, '%Y%m%d_%H%M%S') + ".png"
        subprocess.call(['ffmpeg', '-ss', '00:00:01', '-i', '/var/www/videos/' + videoLoc, '-s', '384x216', '-vframes', '1', '/var/www/videos/' + thumbnailLoc])
        newVideo.thumbnailLocation = thumbnailLoc


    if request.form['videoTitle'] != "":
        newVideo.channelName = strip_html(request.form['videoTitle'])
    else:
        newVideo.channelName = currentTime

    newVideo.description = strip_html(request.form['videoDescription'])

    if os.path.isfile(videoPath):
        newVideo.pending = False
        db.session.add(newVideo)
        db.session.commit()

        if ChannelQuery.imageLocation is None:
            channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
        else:
            channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + ChannelQuery.imageLocation)
        newLog(4, "File Upload Successful - Username:" + current_user.username)

        runWebhook(ChannelQuery.id, 6, channelname=ChannelQuery.channelName,
                   channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(ChannelQuery.id)),
                   channeltopic=get_topicName(ChannelQuery.topic),
                   channelimage=channelImage, streamer=get_userName(ChannelQuery.owningUser),
                   channeldescription=ChannelQuery.description, videoname=newVideo.channelName,
                   videodate=newVideo.videoDate, videodescription=newVideo.description,
                   videotopic=get_topicName(newVideo.topic),
                   videourl=(sysSettings.siteProtocol + sysSettings.siteAddress + '/play/' + str(newVideo.id)),
                   videothumbnail=(sysSettings.siteProtocol + sysSettings.siteAddress + '/videos/' + newVideo.thumbnailLocation))
        try:
            processSubscriptions(ChannelQuery.id,
                             sysSettings.siteName + " - " + ChannelQuery.channelName + " has posted a new video",
                             "<html><body><img src='" + sysSettings.siteProtocol + sysSettings.siteAddress + sysSettings.systemLogo + "'><p>Channel " + ChannelQuery.channelName + " has posted a new video titled <u>" + newVideo.channelName +
                             "</u> to the channel.</p><p>Click this link to watch<br><a href='" + sysSettings.siteProtocol + sysSettings.siteAddress + "/play/" + str(newVideo.id) + "'>" + newVideo.channelName + "</a></p>")
        except:
            newLog(0, "Subscriptions Failed due to possible misconfiguration")

    db.session.close()
    flash("Video upload complete")
    return redirect(url_for('view_vid_page', videoID=newVideo.id))

@app.route('/unsubscribe')
def unsubscribe_page():
    if 'email' in request.args:
        emailAddress = request.args.get("email")
        userQuery = Sec.User.query.filter_by(email=emailAddress).first()
        if userQuery != None:
            subscriptionQuery = subscriptions.channelSubs.query.filter_by(userID=userQuery.id).all()
            for sub in subscriptionQuery:
                db.session.delete(sub)
            db.session.commit()
    return emailAddress + " has been removed from all subscriptions"

@app.route('/settings/user', methods=['POST','GET'])
@login_required
def user_page():
    if request.method == 'GET':
        sysSettings = settings.settings.query.first()
        return render_template(checkOverride('userSettings.html'))
    elif request.method == 'POST':
        emailAddress = request.form['emailAddress']
        password1 = request.form['password1']
        password2 = request.form['password2']
        biography = request.form['biography']

        if password1 != "":
            if password1 == password2:
                newPassword = hash_password(password1)
                current_user.password = newPassword
                newLog(1, "User Password Changed - Username:" + current_user.username)
                flash("Password Changed")
            else:
                flash("Passwords Don't Match!")

        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename != '':
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

        current_user.email = emailAddress

        current_user.biography = biography
        newLog(1, "User Info Updated - Username:" + current_user.username)
        db.session.commit()

    return redirect(url_for('user_page'))

@app.route('/settings/user/subscriptions')
@login_required
def subscription_page():
    sysSettings = settings.settings.query.first()
    channelSubList = subscriptions.channelSubs.query.filter_by(userID=current_user.id).all()

    return render_template(checkOverride('subscriptions.html'), channelSubList=channelSubList)

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
                    newLog(3, "User Added Invite Code to Account - Username:" + current_user.username + " Channel ID #" + str(inviteCodeQuery.channelID))
                    flash("Added Invite Code to Channel", "success")
                    if 'redirectURL' in request.args:
                        return redirect(request.args.get("redirectURL"))
                else:
                    flash("Invite Code Already Applied", "error")
            else:
                newLog(3, "User Attempted to add Expired Invite Code to Account - Username:" + current_user.username + " Channel ID #" + str(inviteCodeQuery.channelID))
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

                    newLog(1, "User " + current_user.username + " deleted Topic " + str(topicQuery.name))
                    db.session.delete(topicQuery)
                    db.session.commit()
                    flash("Topic Deleted")
                    return redirect(url_for('admin_page',page="topics"))

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

                    newLog(1, "User " + current_user.username + " deleted Channel " + str(channelQuery.id))
                    db.session.delete(channelQuery)
                    db.session.commit()

                    flash("Channel Deleted")
                    return redirect(url_for('admin_page', page="channels"))

                elif setting == "users":
                    userID = int(request.args.get("userID"))

                    userQuery = Sec.User.query.filter_by(id=userID).first()

                    if userQuery != None:

                        commentQuery = comments.videoComments.query.filter_by(userID=int(userID)).all()
                        for comment in commentQuery:
                            db.session.delete(comment)
                        db.session.commit()

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

                                for clip in vid.clips:
                                    db.session.delete(clip)

                                db.session.delete(vid)
                            for upvote in chan.upvotes:
                                db.session.delete(upvote)

                            filePath = '/var/www/videos/' + chan.channelLoc

                            if filePath != '/var/www/videos/':
                                shutil.rmtree(filePath, ignore_errors=True)

                            db.session.delete(chan)

                        flash("User " + str(userQuery.username) + " Deleted")
                        newLog(1, "User " + current_user.username + " deleted User " + str(userQuery.username))

                        db.session.delete(userQuery)
                        db.session.commit()

                        return redirect(url_for('admin_page', page="users"))

                elif setting == "userRole":
                    userID = int(request.args.get("userID"))
                    roleID = int(request.args.get("roleID"))

                    userQuery = Sec.User.query.filter_by(id=userID).first()
                    roleQuery = Sec.Role.query.filter_by(id=roleID).first()

                    if userQuery != None and roleQuery != None:
                        user_datastore.remove_role_from_user(userQuery,roleQuery.name)
                        db.session.commit()
                        newLog(1, "User " + current_user.username + " Removed Role " + roleQuery.name + " from User" + userQuery.username)
                        flash("Removed Role from User")

                    else:
                        flash("Invalid Role or User!")
                    return redirect(url_for('admin_page', page="users"))

            elif action == "add":
                if setting == "userRole":
                    userID = int(request.args.get("userID"))
                    roleName = str(request.args.get("roleName"))

                    userQuery = Sec.User.query.filter_by(id=userID).first()
                    roleQuery = Sec.Role.query.filter_by(name=roleName).first()

                    if userQuery != None and roleQuery != None:
                        user_datastore.add_role_to_user(userQuery, roleQuery.name)
                        db.session.commit()
                        newLog(1, "User " + current_user.username + " Added Role " + roleQuery.name + " to User " + userQuery.username)
                        flash("Added Role to User")
                    else:
                        flash("Invalid Role or User!")
                    return redirect(url_for('admin_page', page="users"))
            elif action == "toggleActive":
                if setting == "users":
                    userID = int(request.args.get("userID"))
                    userQuery = Sec.User.query.filter_by(id=userID).first()
                    if userQuery != None:
                        if userQuery.active == True:
                            userQuery.active = False
                            newLog(1, "User " + current_user.username + " Disabled User " + userQuery.username)
                            flash("User Disabled")
                        else:
                            userQuery.active = True
                            newLog(1, "User " + current_user.username + " Enabled User " + userQuery.username)
                            flash("User Enabled")
                        db.session.commit()
                    return redirect(url_for('admin_page', page="users"))
            elif action == "backup":
                dbTables = db.engine.table_names()
                dbDump = {}
                for table in dbTables:
                    for c in db.Model._decl_class_registry.values():
                        if hasattr(c, '__table__') and c.__tablename__ == table:
                            tableDict = table2Dict(c)
                            dbDump[table] = tableDict
                userQuery = Sec.User.query.all()
                dbDump['roles'] = {}
                for user in userQuery:
                    userroles = user.roles
                    dbDump['roles'][user.username] = []
                    for role in userroles:
                        dbDump['roles'][user.username].append(role.name)
                dbDumpJson = json.dumps(dbDump)
                newLog(1, "User " + current_user.username + " Performed DB Backup Dump")
                return Response(dbDumpJson, mimetype='application/json', headers={'Content-Disposition':'attachment;filename=OSPBackup-' + str(datetime.datetime.now()) + '.json'})

            return redirect(url_for('admin_page'))

        page = None
        if request.args.get('page') is not None:
            page = str(request.args.get("page"))
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
            try:
                remoteSHA = None
                if repo != None:
                    repoSHA = str(repo.head.object.hexsha)
                    branch = repo.active_branch
                    branch = branch.name
                    remote = repo.remotes.origin.fetch()[0].commit
                    remoteSHA = str(remote)
            except:
                validGitRepo = False
                branch = "Local Install"


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

        nginxStatDataRequest = requests.get('http://127.0.0.1:9000/stats')
        nginxStatData = (json.loads(json.dumps(xmltodict.parse(nginxStatDataRequest.text))))

        globalWebhookQuery = webhook.globalWebhook.query.all()

        #hubServerQuery = hubConnection.hubServers.query.all()
        #hubRegistrationQuery = hubConnection.hubConnection.query.all()

        themeList = []
        themeDirectorySearch = os.listdir("./templates/themes/")
        for theme in themeDirectorySearch:
            hasJSON = os.path.isfile("./templates/themes/" + theme + "/theme.json")
            if hasJSON:
                themeList.append(theme)

        logsList = logs.logs.query.order_by(logs.logs.timestamp.desc()).limit(250)

        newLog(1, "User " + current_user.username + " Accessed Admin Interface")

        return render_template(checkOverride('admin.html'), appDBVer=appDBVer, userList=userList, roleList=roleList, channelList=channelList, streamList=streamList, topicsList=topicsList, repoSHA=repoSHA,repoBranch=branch,
                               remoteSHA=remoteSHA, themeList=themeList, statsViewsDay=statsViewsDay, viewersTotal=viewersTotal, currentViewers=currentViewers, nginxStatData=nginxStatData, globalHooks=globalWebhookQuery,
                               logsList=logsList, page=page)
    elif request.method == 'POST':

        settingType = request.form['settingType']

        if settingType == "system":

            serverName = request.form['serverName']
            serverProtocol = request.form['siteProtocol']
            serverAddress = request.form['serverAddress']
            smtpSendAs = request.form['smtpSendAs']
            smtpAddress = request.form['smtpAddress']
            smtpPort = request.form['smtpPort']
            smtpUser = request.form['smtpUser']
            smtpPassword = request.form['smtpPassword']
            serverMessage = request.form['serverMessage']
            theme = request.form['theme']

            recordSelect = False
            uploadSelect = False
            adaptiveStreaming = False
            showEmptyTables = False
            allowComments = False
            smtpTLS = False
            smtpSSL = False

            if 'recordSelect' in request.form:
                recordSelect = True

            if 'uploadSelect' in request.form:
                uploadSelect = True

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
                    systemLogo = "/images/" + filename

            validAddress = formatSiteAddress(serverAddress)
            try:
                externalIP = socket.gethostbyname(validAddress)
            except socket.gaierror:
                flash("Invalid Server Address/IP", "error")
                return redirect(url_for("admin_page", page="settings"))

            sysSettings.siteName = serverName
            sysSettings.siteProtocol = serverProtocol
            sysSettings.siteAddress = serverAddress
            sysSettings.smtpSendAs = smtpSendAs
            sysSettings.smtpAddress = smtpAddress
            sysSettings.smtpPort = smtpPort
            sysSettings.smtpUsername = smtpUser
            sysSettings.smtpPassword = smtpPassword
            sysSettings.smtpTLS = smtpTLS
            sysSettings.smtpSSL = smtpSSL
            sysSettings.allowRecording = recordSelect
            sysSettings.allowUploads = uploadSelect
            sysSettings.adaptiveStreaming = adaptiveStreaming
            sysSettings.showEmptyTables = showEmptyTables
            sysSettings.allowComments = allowComments
            sysSettings.systemTheme = theme
            sysSettings.serverMessage = serverMessage
            if systemLogo != None:
                sysSettings.systemLogo = systemLogo

            db.session.commit()

            sysSettings = settings.settings.query.first()

            app.config.update(
                SERVER_NAME=None,
                SECURITY_EMAIL_SENDER=sysSettings.smtpSendAs,
                MAIL_DEFAULT_SENDER=sysSettings.smtpSendAs,
                MAIL_SERVER=sysSettings.smtpAddress,
                MAIL_PORT=sysSettings.smtpPort,
                MAIL_USE_SSL=sysSettings.smtpSSL,
                MAIL_USE_TLS=sysSettings.smtpTLS,
                MAIL_USERNAME=sysSettings.smtpUsername,
                MAIL_PASSWORD=sysSettings.smtpPassword,
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

            themeList = []
            themeDirectorySearch = os.listdir("./templates/themes/")
            for theme in themeDirectorySearch:
                hasJSON = os.path.isfile("./templates/themes/" + theme + "/theme.json")
                if hasJSON:
                    themeList.append(theme)

            newLog(1, "User " + current_user.username + " altered System Settings")

            return redirect(url_for('admin_page', page="settings"))

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
            return redirect(url_for('admin_page', page="topics"))

        elif settingType == "newuser":

            password = request.form['password1']
            email = request.form['emailaddress']
            username = request.form['username']

            passwordhash = utils.hash_password(password)

            user_datastore.create_user(email=email, username=username, password=passwordhash)
            db.session.commit()

            user = Sec.User.query.filter_by(username=username).first()
            user_datastore.add_role_to_user(user, 'User')
            db.session.commit()
            return redirect(url_for('admin_page', page="users"))

        return redirect(url_for('admin_page'))

#@app.route('/settings/admin/hub', methods=['POST', 'GET'])
#@login_required
#@roles_required('Admin')
#def admin_hub_page():
#    sysSettings = settings.settings.query.first()
#    if request.method == "POST":
#        if "action" in request.form:
#            action = request.form["action"]
#            if action == "addConnection":
#                if "hubServer" in request.form:
#                    hubServer = int(request.form["hubServer"])
#
#                    hubServerQuery = hubConnection.hubServers.query.filter_by(id=hubServer).first()
#
#                    if hubServerQuery != None:
#                        r = None

#                        existingConnectionRequest = hubConnection.hubConnection.query.filter_by(hubServer=hubServerQuery.id).first()
#                        if existingConnectionRequest != None:
#                            try:
#                                r = requests.delete(hubServerQuery.serverAddress + '/apiv1/servers', data={'verificationToken': existingConnectionRequest.verificationToken, 'serverAddress': sysSettings.siteAddress})
#                            except requests.exceptions.Timeout:
#                                pass
#                            except requests.exceptions.ConnectionError:
#                                pass
#                            db.session.delete(existingConnectionRequest)
#                            db.session.commit()

#                        newTokenRequest = hubConnection.hubConnection(hubServerQuery.id)
#                        try:
#                            r = requests.post(hubServerQuery.serverAddress + '/apiv1/servers', data={'verificationToken': newTokenRequest.verificationToken, 'serverAddress': sysSettings.siteAddress})
#                        except requests.exceptions.Timeout:
#                            pass
#                        except requests.exceptions.ConnectionError:
#                            pass
#                        if r != None:
#                            if r.status_code == 200:
#                                db.session.add(newTokenRequest)
#                                db.session.commit()
#                                flash("Successfully Added to Hub", "success")
#                                return redirect(url_for('admin_page', page="hub"))
#                            else:
#                                flash("Failed to Add to Hub Due to Server Error")
#                                return redirect(url_for('admin_page', page="hub"))
#                flash("Failed to Add to Hub")
#    if request.method == "GET":
#        if request.args.get("action") is not None:
#            action = request.args.get("action")
#            if action == "deleteConnection":
#                if request.args.get("connectionID"):
#                    connection = hubConnection.hubConnection.query.filter_by(id=int(request.args.get("connectionID"))).first()
#                    try:
#                        r = requests.delete(connection.server.serverAddress + '/apiv1/servers', data={'verificationToken': connection.verificationToken, 'serverAddress': sysSettings.siteAddress})
#                    except requests.exceptions.Timeout:
#                        flash("Unable to Remove from Hub Server Due to Timeout", "error")
#                        return redirect(url_for('admin_page', page="hub"))
#                    except requests.exceptions.ConnectionError:
#                        flash("Unable to Remove from Hub Server Due to Connection Error", "error")
#                        return redirect(url_for('admin_page', page="hub"))
#                    if r.status_code == 200:
#                        db.session.delete(connection)
#                        db.session.commit()
#                        flash("Successfully Removed from Hub","success")
#                        return redirect(url_for('admin_page', page="hub"))
#                    else:
#                        flash("Unable to Remove from Hub Server Due to Connection Error", "error")
#                        return redirect(url_for('admin_page', page="hub"))
#            if action == "deleteServer":
#                if request.args.get("serverID"):
#                    serverQuery = hubConnection.hubServers.query.filter_by(id=int(request.args.get("serverID"))).first()
#                    if serverQuery != None:
#                        if serverQuery.serverAddress == hubURL:
#                            flash("Unable to Delete Default Hub", "error")
#                            return redirect(url_for('admin_page', page="hub"))
#                        else:
#                            db.session.delete(serverQuery)
#                            db.session.commit()
#                            flash("Successfully Deleted Hub", "success")
#                            return redirect(url_for('admin_page', page="hub"))
#
#    return redirect(url_for('admin_page', page="hub"))

@app.route('/settings/dbRestore', methods=['POST'])
def settings_dbRestore():
    validRestoreAttempt = False
    if settings.settings.query.all() == []:
        validRestoreAttempt = True
    elif current_user.is_authenticated:
        if current_user.has_role("Admin"):
            validRestoreAttempt = True

    if validRestoreAttempt == True:

        restoreJSON = None
        if 'restoreData' in request.files:
            file = request.files['restoreData']
            if file.filename != '':
                restoreJSON = file.read()
        if restoreJSON != None:
            restoreDict = json.loads(restoreJSON)

            ## Restore Settings

            serverSettings = settings.settings(restoreDict['settings'][0]['siteName'],
                                               restoreDict['settings'][0]['siteProtocol'],
                                               restoreDict['settings'][0]['siteAddress'],
                                               restoreDict['settings'][0]['smtpAddress'],
                                               int(restoreDict['settings'][0]['smtpPort']),
                                               eval(restoreDict['settings'][0]['smtpTLS']),
                                               eval(restoreDict['settings'][0]['smtpSSL']),
                                               restoreDict['settings'][0]['smtpUsername'],
                                               restoreDict['settings'][0]['smtpPassword'],
                                               restoreDict['settings'][0]['smtpSendAs'],
                                               eval(restoreDict['settings'][0]['allowRecording']),
                                               eval(restoreDict['settings'][0]['allowUploads']),
                                               eval(restoreDict['settings'][0]['adaptiveStreaming']),
                                               eval(restoreDict['settings'][0]['showEmptyTables']),
                                               eval(restoreDict['settings'][0]['allowComments']), version)
            serverSettings.id = int(restoreDict['settings'][0]['id'])
            serverSettings.systemTheme = restoreDict['settings'][0]['systemTheme']
            serverSettings.systemLogo = restoreDict['settings'][0]['systemLogo']
            if 'serverMessage' in restoreDict['settings'][0]:
                serverSettings.serverMessage = restoreDict['settings'][0]['serverMessage']

            # Remove Old Settings
            oldSettings = settings.settings.query.all()
            for row in oldSettings:
                db.session.delete(row)
            db.session.commit()

            db.session.add(serverSettings)
            db.session.commit()

            sysSettings = settings.settings.query.first()

            if settings != None:
                app.config.update(
                    SERVER_NAME=None,
                    SECURITY_EMAIL_SENDER=sysSettings.smtpSendAs,
                    MAIL_DEFAULT_SENDER=sysSettings.smtpSendAs,
                    MAIL_SERVER=sysSettings.smtpAddress,
                    MAIL_PORT=sysSettings.smtpPort,
                    MAIL_USE_TLS=sysSettings.smtpTLS,
                    MAIL_USE_SSL=sysSettings.smtpSSL,
                    MAIL_USERNAME=sysSettings.smtpUsername,
                    MAIL_PASSWORD=sysSettings.smtpPassword,
                    SECURITY_EMAIL_SUBJECT_PASSWORD_RESET=sysSettings.siteName + " - Password Reset Request",
                    SECURITY_EMAIL_SUBJECT_REGISTER=sysSettings.siteName + " - Welcome!",
                    SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE=sysSettings.siteName + " - Password Reset Notification",
                    SECURITY_EMAIL_SUBJECT_CONFIRM=sysSettings.siteName + " - Email Confirmation Request",
                    SECURITY_FORGOT_PASSWORD_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/forgot_password.html',
                    SECURITY_LOGIN_USER_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/login_user.html',
                    SECURITY_REGISTER_USER_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/register_user.html',
                    SECURITY_RESET_PASSWORD_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/reset_password.html',
                    SECURITY_SEND_CONFIRMATION_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/send_confirmation.html')

                mail = Mail(app)

            ## Restores Users
            oldUsers = Sec.User.query.all()
            for user in oldUsers:
                db.session.delete(user)
            db.session.commit()
            for restoredUser in restoreDict['user']:
                user_datastore.create_user(email=restoredUser['email'], username=restoredUser['username'],
                                           password=restoredUser['password'])
                db.session.commit()
                user = Sec.User.query.filter_by(username=restoredUser['username']).first()
                for roleEntry in restoreDict['roles'][user.username]:
                    user_datastore.add_role_to_user(user, roleEntry)
                user.id = int(restoredUser['id'])
                user.pictureLocation = restoredUser['pictureLocation']
                user.active = eval(restoredUser['active'])
                user.biography = restoredUser['biography']
                if restoredUser['confirmed_at'] != "None":
                    try:
                        user.confirmed_at = datetime.datetime.strptime(restoredUser['confirmed_at'], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        user.confirmed_at = datetime.datetime.strptime(restoredUser['confirmed_at'], '%Y-%m-%d %H:%M:%S.%f')
                db.session.commit()

            ## Restore Topics
            oldTopics = topics.topics.query.all()
            for topic in oldTopics:
                db.session.delete(topic)
            db.session.commit()
            for restoredTopic in restoreDict['topics']:
                topic = topics.topics(restoredTopic['name'], restoredTopic['iconClass'])
                topic.id = int(restoredTopic['id'])
                db.session.add(topic)
            db.session.commit()

            ## Restores Channels
            oldChannels = Channel.Channel.query.all()
            for channel in oldChannels:
                db.session.delete(channel)
            db.session.commit()
            for restoredChannel in restoreDict['Channel']:
                if restoredChannel['owningUser'] != "None":
                    channel = Channel.Channel(int(restoredChannel['owningUser']), restoredChannel['streamKey'],
                                              restoredChannel['channelName'], int(restoredChannel['topic']),
                                              eval(restoredChannel['record']), eval(restoredChannel['chatEnabled']),
                                              eval(restoredChannel['allowComments']), restoredChannel['description'])
                    channel.id = int(restoredChannel['id'])
                    channel.channelLoc = restoredChannel['channelLoc']
                    channel.chatBG = restoredChannel['chatBG']
                    channel.chatTextColor = restoredChannel['chatTextColor']
                    channel.chatAnimation = restoredChannel['chatAnimation']
                    channel.views = int(restoredChannel['views'])
                    channel.protected = eval(restoredChannel['protected'])
                    channel.channelMuted = eval(restoredChannel['channelMuted'])
                    channel.defaultStreamName = restoredChannel['defaultStreamName']
                    channel.showChatJoinLeaveNotification = eval(restoredChannel['showChatJoinLeaveNotification'])
                    channel.imageLocation = restoredChannel['imageLocation']
                    channel.offlineImageLocation = restoredChannel['offlineImageLocation']

                    db.session.add(channel)
                else:
                    flash("Error Restoring Channel: ID# " + str(restoredChannel['id']), "error")
            db.session.commit()
            
            ## Restore Subscriptions
            oldSubscriptions = subscriptions.channelSubs.query.all()
            for sub in oldSubscriptions:
                db.session.delete(sub)
            db.session.commit()

            if 'channelSubs' in restoreDict:
                for restoredChannelSub in restoreDict['channelSubs']:
                    channelID = int(restoredChannelSub['channelID'])
                    userID = int(restoredChannelSub['userID'])

                    channelSub = subscriptions.channelSubs(channelID, userID)
                    channelSub.id = int(restoredChannelSub['id'])
                    db.session.add(channelSub)
                db.session.commit()

            ## Restored Videos - Deletes if not restored to maintain DB
            oldVideos = RecordedVideo.RecordedVideo.query.all()
            for video in oldVideos:
                db.session.delete(video)
            db.session.commit()

            if 'restoreVideos' in request.form:

                for restoredVideo in restoreDict['RecordedVideo']:
                    if restoredVideo['channelID'] != "None":
                        try:
                            video = RecordedVideo.RecordedVideo(int(restoredVideo['owningUser']),
                                                            int(restoredVideo['channelID']), restoredVideo['channelName'],
                                                            int(restoredVideo['topic']), int(restoredVideo['views']),
                                                            restoredVideo['videoLocation'],
                                                            datetime.datetime.strptime(restoredVideo['videoDate'],
                                                                                       '%Y-%m-%d %H:%M:%S'),
                                                            eval(restoredVideo['allowComments']))
                        except ValueError:
                            video = RecordedVideo.RecordedVideo(int(restoredVideo['owningUser']),
                                                                int(restoredVideo['channelID']),
                                                                restoredVideo['channelName'],
                                                                int(restoredVideo['topic']),
                                                                int(restoredVideo['views']),
                                                                restoredVideo['videoLocation'],
                                                                datetime.datetime.strptime(restoredVideo['videoDate'],
                                                                                           '%Y-%m-%d %H:%M:%S.%f'),
                                                                eval(restoredVideo['allowComments']))
                        video.id = int(restoredVideo['id'])
                        video.description = restoredVideo['description']
                        if restoredVideo['length'] != "None":
                            video.length = float(restoredVideo['length'])
                        video.thumbnailLocation = restoredVideo['thumbnailLocation']
                        video.pending = eval(restoredVideo['pending'])
                        db.session.add(video)
                    else:
                        flash("Error Restoring Recorded Video: ID# " + str(restoredVideo['id']), "error")
                db.session.commit()

            oldClips = RecordedVideo.Clips.query.all()
            for clip in oldClips:
                db.session.delete(clip)
            db.session.commit()
            if 'restoreVideos' in request.form:
                for restoredClip in restoreDict['Clips']:
                    if restoredClip['parentVideo'] != "None":
                        newClip = RecordedVideo.Clips(int(restoredClip['parentVideo']), float(restoredClip['startTime']),
                                                      float(restoredClip['endTime']), restoredClip['clipName'],
                                                      restoredClip['description'])
                        newClip.id = int(restoredClip['id'])
                        newClip.views = int(restoredClip['views'])
                        newClip.thumbnailLocation = restoredClip['thumbnailLocation']
                        db.session.add(newClip)
                    else:
                        flash("Error Restoring Clip: ID# " + str(restoredClip['id']), "error")
                db.session.commit()

            ## Restores API Keys
            oldAPI = apikey.apikey.query.all()
            for api in oldAPI:
                db.session.delete(api)
            db.session.commit()

            for restoredAPIKey in restoreDict['apikey']:
                if restoredAPIKey['userID'] != "None":
                    key = apikey.apikey(int(restoredAPIKey['userID']), int(restoredAPIKey['type']),
                                        restoredAPIKey['description'], 0)
                    key.id = int(restoredAPIKey['id'])
                    key.key = restoredAPIKey['key']
                    try:
                        key.createdOn = datetime.datetime.strptime(restoredAPIKey['createdOn'], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        key.createdOn = datetime.datetime.strptime(restoredAPIKey['createdOn'], '%Y-%m-%d %H:%M:%S.%f')
                    try:
                        key.expiration = datetime.datetime.strptime(restoredAPIKey['expiration'], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        key.expiration = datetime.datetime.strptime(restoredAPIKey['expiration'], '%Y-%m-%d %H:%M:%S.%f')
                    db.session.add(key)
                else:
                    flash("Error Restoring API Key: ID# " + str(restoredAPIKey['id']), "error")
            db.session.commit()

            ## Restores Webhooks
            oldWebhooks = webhook.webhook.query.all()
            for hook in oldWebhooks:
                db.session.delete(hook)
            db.session.commit()

            for restoredWebhook in restoreDict['webhook']:
                if restoredWebhook['channelID'] != "None":
                    hook = webhook.webhook(restoredWebhook['name'], int(restoredWebhook['channelID']),
                                           restoredWebhook['endpointURL'], restoredWebhook['requestHeader'],
                                           restoredWebhook['requestPayload'], int(restoredWebhook['requestType']),
                                           int(restoredWebhook['requestTrigger']))
                    db.session.add(hook)
                else:
                    flash("Error Restoring Webook ID# " + restoredWebhook['id'], "error")
            db.session.commit()

            ## Restores Global Webhooks
            oldWebhooks = webhook.globalWebhook.query.all()
            for hook in oldWebhooks:
                db.session.delete(hook)
            db.session.commit()

            for restoredWebhook in restoreDict['global_webhook']:
                hook = webhook.globalWebhook(restoredWebhook['name'], restoredWebhook['endpointURL'],
                                             restoredWebhook['requestHeader'], restoredWebhook['requestPayload'],
                                             int(restoredWebhook['requestType']), int(restoredWebhook['requestTrigger']))
                db.session.add(hook)
            db.session.commit()

            ## Restores Views
            oldViews = views.views.query.all()
            for view in oldViews:
                db.session.delete(view)
            db.session.commit()

            for restoredView in restoreDict['views']:
                if not (int(restoredView['viewType']) == 1 and 'restoreVideos' not in request.form):
                    view = views.views(int(restoredView['viewType']), int(restoredView['itemID']))
                    view.id = int(restoredView['id'])
                    try:
                        view.date = datetime.datetime.strptime(restoredView['date'], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        view.date = datetime.datetime.strptime(restoredView['date'], '%Y-%m-%d %H:%M:%S.%f')
                    db.session.add(view)
            db.session.commit()

            ## Restores Invites
            oldInviteCode = invites.inviteCode.query.all()
            for code in oldInviteCode:
                db.session.delete(code)
            db.session.commit()

            for restoredInviteCode in restoreDict['inviteCode']:
                if restoredInviteCode['channelID'] != "None":
                    code = invites.inviteCode(0, int(restoredInviteCode['channelID']))
                    code.id = int(restoredInviteCode['id'])
                    if restoredInviteCode['expiration'] != "None":
                        try:
                            code.expiration = datetime.datetime.strptime(restoredInviteCode['expiration'],
                                                                     '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            code.expiration = datetime.datetime.strptime(restoredInviteCode['expiration'],
                                                                         '%Y-%m-%d %H:%M:%S.%f')
                    else:
                        code.expiration = None
                    code.uses = int(restoredInviteCode['uses'])
                    db.session.add(code)
                else:
                    flash("Error Invite Code: ID# " + str(restoredInviteCode['id']), "error")
            db.session.commit()

            oldInvitedViewers = invites.invitedViewer.query.all()
            for invite in oldInvitedViewers:
                db.session.delete(invite)
            db.session.commit()

            for restoredInvitedViewer in restoreDict['invitedViewer']:
                if restoredInvitedViewer['channelID'] != "None" and restoredInvitedViewer['userID'] != "None":
                    invite = invites.invitedViewer(int(restoredInvitedViewer['userID']),
                                                   int(restoredInvitedViewer['channelID']), 0, None)
                    invite.id = int(restoredInvitedViewer['id'])
                    try:
                        invite.addedDate = datetime.datetime.strptime(restoredInvitedViewer['addedDate'],
                                                                  '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        invite.addedDate = datetime.datetime.strptime(restoredInvitedViewer['addedDate'],
                                                                      '%Y-%m-%d %H:%M:%S.%f')
                    try:
                        invite.expiration = datetime.datetime.strptime(restoredInvitedViewer['expiration'],
                                                                   '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        invite.expiration = datetime.datetime.strptime(restoredInvitedViewer['expiration'],
                                                                       '%Y-%m-%d %H:%M:%S.%f')
                    if 'inviteCode' in restoredInvitedViewer:
                        if restoredInvitedViewer['inviteCode'] != None:
                            invite.inviteCode = int(restoredInvitedViewer['inviteCode'])
                    db.session.add(invite)
                else:
                    flash("Error Restoring Invited Viewer: ID# " + str(restoredInvitedViewer['id']), "error")
            db.session.commit()

            ## Restores Comments
            oldComments = comments.videoComments.query.all()
            for comment in oldComments:
                db.session.delete(comment)
            db.session.commit()

            if 'restoreVideos' in request.form:
                for restoredComment in restoreDict['videoComments']:
                    if restoredComment['userID'] != "None" and restoredComment['videoID'] != "None":
                        comment = comments.videoComments(int(restoredComment['userID']), restoredComment['comment'],
                                                         int(restoredComment['videoID']))
                        comment.id = int(restoredComment['id'])
                        try:
                            comment.timestamp = datetime.datetime.strptime(restoredComment['timestamp'], '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            comment.timestamp = datetime.datetime.strptime(restoredComment['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
                        db.session.add(comment)
                    else:
                        flash("Error Restoring Video Comment: ID# " + str(restoredComment['id']), "error")
                db.session.commit()

            ## Restores Ban List
            oldBanList = banList.banList.query.all()
            for ban in oldBanList:
                db.session.delete(ban)
            db.session.commit()

            for restoredBan in restoreDict['ban_list']:
                if restoredBan['channelLoc'] != "None" and restoredBan['userID'] != "None":
                    ban = banList.banList(restoredBan['channelLoc'], int(restoredBan['userID']))
                    ban.id = int(restoredBan['id'])
                    db.session.add(ban)
                else:
                    flash("Error Restoring Channel Ban Entry: ID# " + str(restoredBan['id']), "error")
            db.session.commit()

            ## Restores Upvotes
            oldChannelUpvotes = upvotes.channelUpvotes.query.all()
            for upvote in oldChannelUpvotes:
                db.session.delete(upvote)
            db.session.commit()
            oldStreamUpvotes = upvotes.streamUpvotes.query.all()
            for upvote in oldStreamUpvotes:
                db.session.delete(upvote)
            db.session.commit()
            oldVideoUpvotes = upvotes.videoUpvotes.query.all()
            for upvote in oldVideoUpvotes:
                db.session.delete(upvote)
            db.session.commit()
            oldCommentUpvotes = upvotes.commentUpvotes.query.all()
            for upvote in oldCommentUpvotes:
                db.session.delete(upvote)
            db.session.commit()
            oldClipUpvotes = upvotes.clipUpvotes.query.all()
            for upvote in oldClipUpvotes:
                db.session.delete(upvote)
            db.session.commit()

            for restoredUpvote in restoreDict['channel_upvotes']:
                if restoredUpvote['userID'] != "None" and restoredUpvote['channelID'] != "None":
                    upvote = upvotes.channelUpvotes(int(restoredUpvote['userID']), int(restoredUpvote['channelID']))
                    upvote.id = int(restoredUpvote['id'])
                    db.session.add(upvote)
                else:
                    flash("Error Restoring Upvote: ID# " + str(restoredUpvote['id']), "error")
            db.session.commit()
            for restoredUpvote in restoreDict['stream_upvotes']:
                if restoredUpvote['userID'] != "None" and restoredUpvote['streamID'] != "None":
                    upvote = upvotes.streamUpvotes(int(restoredUpvote['userID']), int(restoredUpvote['streamID']))
                    upvote.id = int(restoredUpvote['id'])
                    db.session.add(upvote)
                else:
                    flash("Error Restoring Upvote: ID# " + str(restoredUpvote['id']), "error")
            db.session.commit()
            if 'restoreVideos' in request.form:
                for restoredUpvote in restoreDict['video_upvotes']:
                    if restoredUpvote['userID'] != "None" and restoredUpvote['videoID'] != "None":
                        upvote = upvotes.videoUpvotes(int(restoredUpvote['userID']), int(restoredUpvote['videoID']))
                        upvote.id = int(restoredUpvote['id'])
                        db.session.add(upvote)
                    flash("Error Restoring Upvote: ID# " + str(restoredUpvote['id']), "error")
                db.session.commit()
                for restoredUpvote in restoreDict['clip_upvotes']:
                    if restoredUpvote['userID'] != "None" and restoredUpvote['clipID'] != "None":
                        upvote = upvotes.clipUpvotes(int(restoredUpvote['userID']), int(restoredUpvote['clipID']))
                        upvote.id = int(restoredUpvote['id'])
                        db.session.add(upvote)
                    flash("Error Restoring Upvote: ID# " + str(restoredUpvote['id']), "error")
                db.session.commit()
            for restoredUpvote in restoreDict['comment_upvotes']:
                if restoredUpvote['userID'] != "None" and restoredUpvote['commentID'] != "None":
                    upvote = upvotes.commentUpvotes(int(restoredUpvote['userID']), int(restoredUpvote['commentID']))
                    upvote.id = int(restoredUpvote['id'])
                    db.session.add(upvote)
                else:
                    flash("Error Restoring Upvote: ID# " + str(restoredUpvote['id']), "error")
            db.session.commit()

            # Import Theme Data into Theme Dictionary
            with open('templates/themes/' + sysSettings.systemTheme + '/theme.json') as f:
                global themeData

                themeData = json.load(f)

            flash("Database Restored from Backup", "success")
            session.clear()
            return redirect(url_for('main_page', page="backup"))

    else:
        if settings.settings.query.all() != []:
            flash("Invalid Restore Attempt","error")
            return redirect(url_for('main_page'))
        else:
            return redirect(url_for('initialSetup'))


@app.route('/settings/channels', methods=['POST','GET'])
@login_required
def settings_channels_page():
    sysSettings = settings.settings.query.first()
    channelChatBGOptions = [{'name': 'Default', 'value': 'Standard'},{'name': 'Plain White', 'value': 'PlainWhite'}, {'name': 'Deep Space', 'value': 'DeepSpace'}, {'name': 'Blood Red', 'value': 'BloodRed'}, {'name': 'Terminal', 'value': 'Terminal'}, {'name': 'Lawrencium', 'value': 'Lawrencium'}, {'name': 'Lush', 'value': 'Lush'}, {'name': 'Transparent', 'value': 'Transparent'}]
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

        chatJoinNotifications = False
        if 'chatJoinNotificationSelect' in request.form:
            chatJoinNotifications = True

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

            defaultstreamName = request.form['channelStreamName']

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
                requestedChannel.showChatJoinLeaveNotification = chatJoinNotifications
                requestedChannel.chatAnimation = chatAnimation
                requestedChannel.chatTextColor = chatTextColor
                requestedChannel.protected = protection
                requestedChannel.defaultStreamName = defaultstreamName

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

    return render_template(checkOverride('user_channels.html'), channels=user_channels, topics=topicList, viewStats=user_channels_stats, channelChatBGOptions=channelChatBGOptions, channelChatAnimationOptions=channelChatAnimationOptions)

@app.route('/settings/api', methods=['GET'])
@login_required
@roles_required('Streamer')
def settings_apikeys_page():
    sysSettings = settings.settings.query.first()
    apiKeyQuery = apikey.apikey.query.filter_by(userID=current_user.id).all()
    return render_template(checkOverride('apikeys.html'),apikeys=apiKeyQuery)

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
        serverProtocol = str(request.form['siteProtocol'])
        serverAddress = str(request.form['serverAddress'])
        smtpSendAs = request.form['smtpSendAs']
        smtpAddress = request.form['smtpAddress']
        smtpPort = request.form['smtpPort']
        smtpUser = request.form['smtpUser']
        smtpPassword = request.form['smtpPassword']

        recordSelect = False
        uploadSelect = False
        adaptiveStreaming = False
        showEmptyTables = False
        allowComments = False
        smtpTLS = False
        smtpSSL = False

        if 'recordSelect' in request.form:
            recordSelect = True

        if 'uploadSelect' in request.form:
            uploadSelect = True

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

        validAddress = formatSiteAddress(serverAddress)
        try:
            externalIP = socket.gethostbyname(validAddress)
        except socket.gaierror:
            flash("Invalid Server Address/IP", "error")
            return redirect(url_for("initialSetup"))

        if password1 == password2:

            passwordhash = utils.hash_password(password1)

            user_datastore.create_user(email=email, username=username, password=passwordhash)
            db.session.commit()
            user = Sec.User.query.filter_by(username=username).first()
            user_datastore.add_role_to_user(user, 'Admin')
            user_datastore.add_role_to_user(user, 'Streamer')
            user_datastore.add_role_to_user(user, 'User')

            serverSettings = settings.settings(serverName, serverProtocol, serverAddress, smtpAddress, smtpPort, smtpTLS, smtpSSL, smtpUser, smtpPassword, smtpSendAs, recordSelect, uploadSelect, adaptiveStreaming, showEmptyTables, allowComments, version)
            db.session.add(serverSettings)
            db.session.commit()

            sysSettings = settings.settings.query.first()

            if settings != None:
                app.config.update(
                    SERVER_NAME=None,
                    SECURITY_EMAIL_SENDER=sysSettings.smtpSendAs,
                    MAIL_DEFAULT_SENDER=sysSettings.smtpSendAs,
                    MAIL_SERVER=sysSettings.smtpAddress,
                    MAIL_PORT=sysSettings.smtpPort,
                    MAIL_USE_TLS=sysSettings.smtpTLS,
                    MAIL_USE_SSL=sysSettings.smtpSSL,
                    MAIL_USERNAME=sysSettings.smtpUsername,
                    MAIL_PASSWORD=sysSettings.smtpPassword,
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

                # Import Theme Data into Theme Dictionary
                with open('templates/themes/' + sysSettings.systemTheme + '/theme.json') as f:
                    global themeData

                    themeData = json.load(f)

        else:
            flash('Passwords do not match')
            return redirect(url_for('main_page'))

    return redirect(url_for('main_page'))

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
        videoList1 = RecordedVideo.RecordedVideo.query.filter(RecordedVideo.RecordedVideo.channelName.contains(search)).all()
        videoList2 = RecordedVideo.RecordedVideo.query.filter(RecordedVideo.RecordedVideo.description.contains(search)).all()
        for video in videoList1:
            videoList.append(video)
        for video in videoList2:
            if video not in videoList:
                videoList.append(video)

        streamList = Stream.Stream.query.filter(Stream.Stream.streamName.contains(search)).all()

        clipList = []
        clipList1 = RecordedVideo.Clips.query.filter(RecordedVideo.Clips.clipName.contains(search)).all()
        clipList2 = RecordedVideo.Clips.query.filter(RecordedVideo.Clips.description.contains(search)).all()
        for clip in clipList1:
            clipList.append(clip)
        for clip in clipList2:
            if clip not in clipList:
                clipList.append(clip)

        return render_template(checkOverride('search.html'), topicList=topicList, streamerList=streamerList, channelList=channelList, videoList=videoList, streamList=streamList, clipList=clipList)

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
            del response.headers["Content-Type"]
            db.session.close()
            return response
        else:
            return abort(401)
    else:
        redirect_path = "/osp-videos/" + str(channelID) + "/" + filename
        response = make_response("")
        response.headers["X-Accel-Redirect"] = redirect_path
        del response.headers["Content-Type"]
        db.session.close()
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
            db.session.close()
            return response
        else:
            return abort(401)
    else:
        redirect_path = "/osp-streamthumbs" + "/" + filename
        response = make_response("")
        response.headers["X-Accel-Redirect"] = redirect_path
        db.session.close()
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
            db.session.close()
            return response
        else:
            return abort(401)
    else:
        redirect_path = "/osp-liveadapt" + "/" + filename
        response = make_response("")
        response.headers["X-Accel-Redirect"] = redirect_path
        db.session.close()
        return response

@app.route('/live-adapt/<string:channelID>/<path:filename>')
def live_adapt_stream_directory_sender(channelID, filename):
    parsedPath = channelID.split("_")
    channelloc = parsedPath[0]
    channelQuery = Channel.Channel.query.filter_by(channelLoc=channelloc).first()
    if channelQuery.protected:
        if check_isValidChannelViewer(channelQuery.id):
            redirect_path = "/osp-liveadapt" + "/" + str(channelID) + "/" + filename
            response = make_response("")
            response.headers["X-Accel-Redirect"] = redirect_path
            db.session.close()
            return response
        else:
            return abort(401)
    else:
        redirect_path = "/osp-liveadapt" + "/" + str(channelID) + "/" + filename
        response = make_response("")
        response.headers["X-Accel-Redirect"] = redirect_path
        db.session.close()
        return response

@app.route('/live/<string:channelID>/<path:filename>')
def live_stream_directory_sender(channelID, filename):
    channelQuery = Channel.Channel.query.filter_by(channelLoc=channelID).first()
    if channelQuery.protected:
        if check_isValidChannelViewer(channelQuery.id):
            redirect_path = "/osp-live" + "/" + str(channelID) + "/" + filename
            response = make_response("")
            response.headers["X-Accel-Redirect"] = redirect_path
            db.session.close()
            return response

        else:
            return abort(401)
    else:
        redirect_path = "/osp-live" + "/" + str(channelID) + "/" + filename
        response = make_response("")
        response.headers["X-Accel-Redirect"] = redirect_path
        db.session.close()
        return response

@app.route('/live-rec/<string:channelID>/<path:filename>')
def live_rec_stream_directory_sender(channelID, filename):
    channelQuery = Channel.Channel.query.filter_by(channelLoc=channelID).first()
    if channelQuery.protected:
        if check_isValidChannelViewer(channelQuery.id):
            redirect_path = "/osp-liverec" + "/" + str(channelID) + "/" + filename
            response = make_response("")
            response.headers["X-Accel-Redirect"] = redirect_path
            db.session.close()
            return response
        else:
            abort(401)
    else:
        redirect_path = "/osp-liverec" + "/" + str(channelID) + "/" + filename
        response = make_response("")
        response.headers["X-Accel-Redirect"] = redirect_path
        db.session.close()
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

                defaultStreamName = normalize_date(str(currentTime))
                if channelRequest.defaultStreamName != "":
                    defaultStreamName = channelRequest.defaultStreamName

                newStream = Stream.Stream(key, defaultStreamName, int(channelRequest.id), channelRequest.topic)
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

    key = request.form['name']
    ipaddress = request.form['addr']

    requestedChannel = Channel.Channel.query.filter_by(channelLoc=key).first()

    authedStream = Stream.Stream.query.filter_by(streamKey=requestedChannel.streamKey).first()

    if authedStream is not None:
        returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Successful Channel Auth', 'key': str(requestedChannel.streamKey), 'channelName': str(requestedChannel.channelName), 'ipAddress': str(ipaddress)}
        print(returnMessage)

        if requestedChannel.imageLocation is None:
            channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
        else:
            channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + requestedChannel.imageLocation)

        runWebhook(requestedChannel.id, 0, channelname=requestedChannel.channelName, channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(requestedChannel.id)), channeltopic=requestedChannel.topic,
                   channelimage=channelImage, streamer=get_userName(requestedChannel.owningUser), channeldescription=requestedChannel.description,
                   streamname=authedStream.streamName, streamurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/view/" + requestedChannel.channelLoc), streamtopic=get_topicName(authedStream.topic),
                   streamimage=(sysSettings.siteProtocol + sysSettings.siteAddress + "/stream-thumb/" + requestedChannel.channelLoc + ".png"))

        try:
            processSubscriptions(requestedChannel.id,
                             sysSettings.siteName + " - " + requestedChannel.channelName + " has started a stream",
                             "<html><body><img src='" + sysSettings.siteProtocol + sysSettings.siteAddress + sysSettings.systemLogo + "'><p>Channel " + requestedChannel.channelName +
                             " has started a new video stream.</p><p>Click this link to watch<br><a href='" + sysSettings.siteProtocol + sysSettings.siteAddress + "/view/" + str(requestedChannel.channelLoc)
                             + "'>" + requestedChannel.channelName + "</a></p>")
        except:
            newLog(0, "Subscriptions Failed due to possible misconfiguration")

        db.session.close()
        return 'OK'
    else:
        returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Failed Channel Auth. No Authorized Stream Key', 'channelName': str(key), 'ipAddress': str(ipaddress)}
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

            returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Stream Closed', 'key': str(key), 'channelName': str(channelRequest.channelName), 'userName':str(channelRequest.owningUser), 'ipAddress': str(ipaddress)}

            print(returnMessage)

            if channelRequest.imageLocation is None:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
            else:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + channelRequest.imageLocation)

            runWebhook(channelRequest.id, 1, channelname=channelRequest.channelName,
                       channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(channelRequest.id)),
                       channeltopic=channelRequest.topic,
                       channelimage=channelImage, streamer=get_userName(channelRequest.owningUser),
                       channeldescription=channelRequest.description,
                       streamname=stream.streamName,
                       streamurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/view/" + channelRequest.channelLoc),
                       streamtopic=get_topicName(stream.topic),
                       streamimage=(sysSettings.siteProtocol + sysSettings.siteAddress + "/stream-thumb/" + channelRequest.channelLoc + ".png"))
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
        channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
    else:
        channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + requestedChannel.imageLocation)

    runWebhook(requestedChannel.id, 6, channelname=requestedChannel.channelName,
               channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(requestedChannel.id)),
               channeltopic=get_topicName(requestedChannel.topic),
               channelimage=channelImage, streamer=get_userName(requestedChannel.owningUser),
               channeldescription=requestedChannel.description, videoname=pendingVideo.channelName,
               videodate=pendingVideo.videoDate, videodescription=pendingVideo.description,videotopic=get_topicName(pendingVideo.topic),
               videourl=(sysSettings.siteProtocol + sysSettings.siteAddress + '/play/' + str(pendingVideo.id)),
               videothumbnail=(sysSettings.siteProtocol + sysSettings.siteAddress + '/videos/' + pendingVideo.thumbnailLocation))

    processSubscriptions(requestedChannel.id, sysSettings.siteName + " - " + requestedChannel.channelName + " has posted a new video",
                         "<html><body><img src='" + sysSettings.siteProtocol + sysSettings.siteAddress + sysSettings.systemLogo + "'><p>Channel " + requestedChannel.channelName + " has posted a new video titled <u>" + pendingVideo.channelName +
                         "</u> to the channel.</p><p>Click this link to watch<br><a href='" + sysSettings.siteProtocol + sysSettings.siteAddress + "/play/" + str(pendingVideo.id) + "'>" + pendingVideo.channelName + "</a></p>")

    while not os.path.exists(fullVidPath):
        time.sleep(1)

    if os.path.isfile(fullVidPath):
        pendingVideo.length = getVidLength(fullVidPath)
        db.session.commit()

    db.session.close()
    return 'OK'

@app.route('/playbackAuth', methods=['POST'])
def playback_auth_handler():
    stream = request.form['name']

    streamQuery = Channel.Channel.query.filter_by(channelLoc=stream).first()
    if streamQuery != None:

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
                            if check_isUserValidRTMPViewer(requestedUser.id,streamQuery.id):
                                db.session.close()
                                return 'OK'
    db.session.close()
    return abort(400)

@app.route('/robots.txt')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])

### Start Socket.IO Functions ###

@socketio.on('testEmail')
def test_email(info):
    sysSettings = settings.settings.query.all()
    validTester = False
    if sysSettings == [] or sysSettings == None:
        validTester = True
    else:
        if current_user.has_role('Admin'):
            validTester = True
    if validTester is True:
        smtpServer = info['smtpServer']
        smtpPort = int(info['smtpPort'])
        smtpTLS = bool(info['smtpTLS'])
        smtpSSL = bool(info['smtpSSL'])
        smtpUsername = info['smtpUsername']
        smtpPassword = info['smtpPassword']
        smtpSender = info['smtpSender']
        smtpReceiver = info['smtpReceiver']

        results = sendTestEmail(smtpServer, smtpPort, smtpTLS, smtpSSL, smtpUsername, smtpPassword, smtpSender, smtpReceiver)
        db.session.close()
        emit('testEmailResults', {'results': str(results)}, broadcast=False)

@socketio.on('toggleChannelSubscription')
def toggle_chanSub(payload):
    if current_user.is_authenticated:
        sysSettings = settings.settings.query.first()
        if 'channelID' in payload:
            channelQuery = Channel.Channel.query.filter_by(id=int(payload['channelID'])).first()
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
                    if current_user.pictureLocation == None:
                        pictureLocation = '/static/img/user2.png'
                    else:
                        pictureLocation = '/images/' + pictureLocation

                    runWebhook(channelQuery.id, 10, channelname=channelQuery.channelName,
                               channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(channelQuery.id)),
                               channeltopic=get_topicName(channelQuery.topic),
                               channelimage=channelImage, streamer=get_userName(channelQuery.owningUser),
                               channeldescription=channelQuery.description,
                               user=current_user.username, userpicture=sysSettings.siteProtocol + sysSettings.siteAddress + pictureLocation)
                else:
                    db.session.delete(currentSubscription)
                db.session.commit()
                db.session.close()
                emit('sendChanSubResults', {'state': subState}, broadcast=False)
    db.session.close()

@socketio.on('cancelUpload')
def handle_videoupload_disconnect(videofilename):
    ospvideofilename = app.config['VIDEO_UPLOAD_TEMPFOLDER'] + '/' + str(videofilename['data'])
    thumbnailFilename = ospvideofilename + '.png'
    videoFilename = ospvideofilename + '.mp4'

    time.sleep(5)

    if os.path.exists(thumbnailFilename) and time.time() - os.stat(thumbnailFilename).st_mtime > 5:
            os.remove(thumbnailFilename)
    if os.path.exists(videoFilename) and time.time() - os.stat(videoFilename).st_mtime > 5:
            os.remove(videoFilename)

@socketio.on('newViewer')
def handle_new_viewer(streamData):
    channelLoc = str(streamData['data'])

    sysSettings = settings.settings.query.first()

    requestedChannel = Channel.Channel.query.filter_by(channelLoc=channelLoc).first()
    stream = Stream.Stream.query.filter_by(streamKey=requestedChannel.streamKey).first()

    userSID = request.sid

    streamSIDList = r.smembers(channelLoc + '-streamSIDList')
    if streamSIDList == None:
        r.sadd(channelLoc + '-streamSIDList', userSID)
    elif userSID.encode('utf-8') not in streamSIDList:
        r.sadd(channelLoc + '-streamSIDList', userSID)

    currentViewers = len(streamSIDList)

    streamName = ""
    streamTopic = 0

    requestedChannel.currentViewers = currentViewers

    if stream is not None:
        stream.currentViewers = currentViewers
        db.session.commit()
        streamName = stream.streamName
        streamTopic = stream.topic
    else:
        streamName = requestedChannel.channelName
        streamTopic = requestedChannel.topic

    if requestedChannel.imageLocation is None:
        channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
    else:
        channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + requestedChannel.imageLocation)

    join_room(streamData['data'])

    if requestedChannel.showChatJoinLeaveNotification == True:
        if current_user.is_authenticated:
            pictureLocation = current_user.pictureLocation
            if current_user.pictureLocation == None:
                pictureLocation = '/static/img/user2.png'
            else:
                pictureLocation = '/images/' + pictureLocation

            streamUserList = r.smembers(channelLoc + '-streamUserList')
            if streamUserList == None:
                r.rpush(channelLoc + '-streamUserList', current_user.username)
            elif current_user.username.encode('utf-8') not in streamUserList:
                r.rpush(channelLoc + '-streamUserList', current_user.username)

            emit('message', {'user':'Server','msg': current_user.username + ' has entered the room.', 'image': pictureLocation}, room=streamData['data'])
            runWebhook(requestedChannel.id, 2, channelname=requestedChannel.channelName,
                       channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(requestedChannel.id)),
                       channeltopic=requestedChannel.topic,
                       channelimage=channelImage, streamer=get_userName(requestedChannel.owningUser),
                       channeldescription=requestedChannel.description,
                       streamname=streamName,
                       streamurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/view/" + requestedChannel.channelLoc),
                       streamtopic=get_topicName(streamTopic),
                       streamimage=(sysSettings.siteProtocol + sysSettings.siteAddress + "/stream-thumb/" + requestedChannel.channelLoc + ".png"),
                       user=current_user.username, userpicture=(sysSettings.siteProtocol + sysSettings.siteAddress + pictureLocation))
        else:
            emit('message', {'user':'Server','msg': 'Guest has entered the room.', 'image': '/static/img/user2.png'}, room=streamData['data'])
            runWebhook(requestedChannel.id, 2, channelname=requestedChannel.channelName,
                       channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(requestedChannel.id)),
                       channeltopic=requestedChannel.topic,
                       channelimage=channelImage, streamer=get_userName(requestedChannel.owningUser),
                       channeldescription=requestedChannel.description,
                       streamname=streamName,
                       streamurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/view/" + requestedChannel.channelLoc),
                       streamtopic=get_topicName(streamTopic),
                       streamimage=(sysSettings.siteProtocol + sysSettings.siteAddress + "/stream-thumb/" + requestedChannel.channelLoc + ".png"),
                       user="Guest", userpicture=(sysSettings.siteProtocol + sysSettings.siteAddress + '/static/img/user2.png'))
    else:
        if current_user.is_authenticated:
            r.rpush(channelLoc + '-streamUserList', current_user.username)

    db.session.commit()
    db.session.close()

@socketio.on('openPopup')
def handle_new_popup_viewer(streamData):
    join_room(streamData['data'])

@socketio.on('removeViewer')
def handle_leaving_viewer(streamData):
    channelLoc = str(streamData['data'])

    requestedChannel = Channel.Channel.query.filter_by(channelLoc=channelLoc).first()
    stream = Stream.Stream.query.filter_by(streamKey=requestedChannel.streamKey).first()

    userSID = request.sid

    streamSIDList = r.smembers(channelLoc + '-streamSIDList')
    if streamSIDList != None:
        r.srem(channelLoc + '-streamSIDList', userSID)

    currentViewers = len(streamSIDList)

    requestedChannel.currentViewers = currentViewers
    if requestedChannel.currentViewers < 0:
        requestedChannel.currentViewers = 0
    db.session.commit()

    if stream is not None:
        stream.currentViewers = currentViewers
        if stream.currentViewers < 0:
            stream.currentViewers = 0
        db.session.commit()
    leave_room(streamData['data'])

    if current_user.is_authenticated:
        streamUserList = r.lrange(channelLoc + '-streamUserList', 0, -1)
        if streamUserList != None:
            r.lrem(channelLoc + '-streamUserList', 1, current_user.username)

        if requestedChannel.showChatJoinLeaveNotification == True:
            pictureLocation = current_user.pictureLocation
            if current_user.pictureLocation == None:
                pictureLocation = '/static/img/user2.png'
            else:
                pictureLocation = '/images/' + pictureLocation

            emit('message', {'user':'Server', 'msg': current_user.username + ' has left the room.', 'image': pictureLocation}, room=streamData['data'])
        else:
            if requestedChannel.showChatJoinLeaveNotification == True:
                emit('message', {'user':'Server', 'msg': 'Guest has left the room.', 'image': '/static/img/user2.png'}, room=streamData['data'])
    db.session.commit()
    db.session.close()

@socketio.on('disconnect')
def disconnect():


    pass

@socketio.on('closePopup')
def handle_leaving_popup_viewer(streamData):
    leave_room(streamData['data'])

@socketio.on('getViewerTotal')
def handle_viewer_total_request(streamData):
    channelLoc = str(streamData['data'])

    viewers = len(r.smembers(channelLoc + '-streamSIDList'))

    streamUserList = r.lrange(channelLoc + '-streamUserList', 0, -1)
    if streamUserList == None:
        streamUserList = []

    decodedStreamUserList = []
    for entry in streamUserList:
        user = entry.decode('utf-8')
        # Prevent Duplicate Usernames in Master List, but allow users to have multiple windows open
        if user not in decodedStreamUserList:
            decodedStreamUserList.append(user)

    db.session.commit()
    db.session.close()
    emit('viewerTotalResponse', {'data': str(viewers), 'userList': decodedStreamUserList})

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
    elif vidType == "clip":
        loc = int(loc)
        totalQuery = upvotes.clipUpvotes.query.filter_by(clipID=loc).all()
        try:
            myVoteQuery = upvotes.clipUpvotes.query.filter_by(userID=current_user.id, clipID=loc).first()
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
    elif vidType == 'clip':
        loc = int(loc)
        myVoteQuery = upvotes.clipUpvotes.query.filter_by(userID=current_user.id, clipID=loc).first()

        if myVoteQuery == None:
            newUpvote = upvotes.clipUpvotes(current_user.id, loc)
            db.session.add(newUpvote)
        else:
            db.session.delete(myVoteQuery)
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

@socketio.on('setScreenShot')
def setScreenShot(message):
    timeStamp = message['timeStamp']

    if 'loc' in message:
        video = message['loc']
        if video != None:
            videoQuery = RecordedVideo.RecordedVideo.query.filter_by(id=int(video)).first()
            if videoQuery != None and videoQuery.owningUser == current_user.id:
                videoLocation = '/var/www/videos/' + videoQuery.videoLocation
                newThumbnailLocation = videoQuery.videoLocation[:-3] + "png"
                videoQuery.thumbnailLocation = newThumbnailLocation
                fullthumbnailLocation = '/var/www/videos/' + newThumbnailLocation
                db.session.commit()
                db.session.close()
                try:
                    os.remove(fullthumbnailLocation)
                except OSError:
                    pass
                result = subprocess.call(['ffmpeg', '-ss', str(timeStamp), '-i', videoLocation, '-s', '384x216', '-vframes', '1', fullthumbnailLocation])
    elif 'clipID' in message:
        clipID = message['clipID']
        clipQuery = RecordedVideo.Clips.query.filter_by(id=int(clipID)).first()
        if clipQuery != None and current_user.id == clipQuery.recordedVideo.owningUser:
            thumbnailLocation = clipQuery.thumbnailLocation
            fullthumbnailLocation = '/var/www/videos/' + thumbnailLocation
            videoLocation = '/var/www/videos/' + clipQuery.recordedVideo.videoLocation
            newClipThumbnail = clipQuery.recordedVideo.channel.channelLoc + '/clips/clip-' + str(clipQuery.id) + '.png'
            fullNewClipThumbnailLocation = '/var/www/videos/' + newClipThumbnail
            clipQuery.thumbnailLocation = newClipThumbnail
            db.session.commit()
            db.session.close()
            try:
                os.remove(fullthumbnailLocation)
            except OSError:
                pass
            result = subprocess.call(['ffmpeg', '-ss', str(timeStamp), '-i', videoLocation, '-s', '384x216', '-vframes', '1', fullNewClipThumbnailLocation])


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
            channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
        else:
            channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + channelQuery.imageLocation)

        runWebhook(channelQuery.id, 4, channelname=channelQuery.channelName,
                   channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(channelQuery.id)),
                   channeltopic=channelQuery.topic,
                   channelimage=channelImage, streamer=get_userName(channelQuery.owningUser),
                   channeldescription=channelQuery.description,
                   streamname=stream.streamName,
                   streamurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/view/" + channelQuery.channelLoc),
                   streamtopic=get_topicName(stream.topic),
                   streamimage=(sysSettings.siteProtocol + sysSettings.siteAddress + "/stream-thumb/" + channelQuery.channelLoc + ".png"))
        db.session.commit()
        db.session.close()

@socketio.on('text')
@limiter.limit("1/second")
def text(message):
    """Sent by a client when the user entered a new message.
    The message is sent to all people in the room."""
    room = message['room']
    msg = strip_html(message['msg'])

    sysSettings = settings.settings.query.first()

    channelQuery = Channel.Channel.query.filter_by(channelLoc=room).first()

    #global streamSIDList

    if channelQuery != None:

        userSID = request.sid
        if userSID.encode('utf-8') not in r.smembers(channelQuery.channelLoc + '-streamSIDList'):
            r.sadd(channelQuery.channelLoc + '-streamSIDList', userSID)
        if current_user.username.encode('utf-8') not in r.lrange(channelQuery.channelLoc + '-streamUserList', 0, -1):
            r.rpush(channelQuery.channelLoc + '-streamUserList', current_user.username)

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
                    channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
                else:
                    channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + channelQuery.imageLocation)

                streamName = None
                streamTopic = None

                if channelQuery.stream != []:
                    streamName = channelQuery.stream[0].streamName
                    streamTopic = channelQuery.stream[0].topic
                else:
                    streamName = channelQuery.channelName
                    streamTopic = channelQuery.topic

                runWebhook(channelQuery.id, 5, channelname=channelQuery.channelName,
                           channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(channelQuery.id)),
                           channeltopic=get_topicName(channelQuery.topic),
                           channelimage=channelImage, streamer=get_userName(channelQuery.owningUser),
                           channeldescription=channelQuery.description,
                           streamname=streamName,
                           streamurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/view/" + channelQuery.channelLoc),
                           streamtopic=get_topicName(streamTopic), streamimage=(sysSettings.siteProtocol + sysSettings.siteAddress + "/stream-thumb/" + channelQuery.channelLoc + ".png"),
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


@socketio.on('getServerResources')
def get_resource_usage(message):
    cpuUsage = psutil.cpu_percent(interval=1)
    memoryUsage = psutil.virtual_memory()[2]
    diskUsage = psutil.disk_usage('/')[3]

    emit('serverResources', {'cpuUsage':cpuUsage,'memoryUsage':memoryUsage, 'diskUsage':diskUsage})

@socketio.on('generateInviteCode')
def generateInviteCode(message):
    selectedInviteCode = str(message['inviteCode'])
    daysToExpire = int(message['daysToExpiration'])
    channelID = int(message['chanID'])

    channelQuery = Channel.Channel.query.filter_by(id=channelID, owningUser=current_user.id).first()

    if channelQuery is not None:
        newInviteCode = invites.inviteCode(daysToExpire, channelID)
        if selectedInviteCode != "":
            inviteCodeQuery = invites.inviteCode.query.filter_by(code=selectedInviteCode).first()
            if inviteCodeQuery is None:
                newInviteCode.code = selectedInviteCode
            else:
                db.session.close()
                return False

        db.session.add(newInviteCode)
        db.session.commit()

        emit('newInviteCode', {'code': str(newInviteCode.code), 'expiration': str(newInviteCode.expiration), 'channelID':str(newInviteCode.channelID)}, broadcast=False)

    else:
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

    invalidTriggers = [20]

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

        if webhookInputAction == 'new' and webhookTrigger not in invalidTriggers:
            newWebHook = webhook.webhook(webhookName, channelID, webhookEndpoint, webhookHeader, webhookPayload, webhookReqType, webhookTrigger)
            db.session.add(newWebHook)
            db.session.commit()
            emit('newWebhookAck', {'webhookName': webhookName, 'requestURL':webhookEndpoint, 'requestHeader':webhookHeader, 'requestPayload':webhookPayload, 'requestType':webhookReqType, 'requestTrigger':webhookTrigger, 'requestID':newWebHook.id, 'channelID':channelID}, broadcast=False)
        elif webhookInputAction == 'edit' and webhookTrigger not in invalidTriggers:
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

@socketio.on('submitGlobalWebhook')
def addChangeGlobalWebhook(message):

    if current_user.has_role('Admin'):
        webhookName = message['webhookName']
        webhookEndpoint = message['webhookEndpoint']
        webhookTrigger = int(message['webhookTrigger'])
        webhookHeader = message['webhookHeader']
        webhookPayload = message['webhookPayload']
        webhookReqType = int(message['webhookReqType'])
        webhookInputAction = message['inputAction']
        webhookInputID = message['webhookInputID']

        if webhookInputAction == 'new':
            newWebHook = webhook.globalWebhook(webhookName, webhookEndpoint, webhookHeader, webhookPayload, webhookReqType, webhookTrigger)
            db.session.add(newWebHook)
            db.session.commit()
            emit('newGlobalWebhookAck', {'webhookName': webhookName, 'requestURL':webhookEndpoint, 'requestHeader':webhookHeader, 'requestPayload':webhookPayload, 'requestType':webhookReqType, 'requestTrigger':webhookTrigger, 'requestID':newWebHook.id}, broadcast=False)
        elif webhookInputAction == 'edit':
            existingWebhookQuery = webhook.globalWebhook.query.filter_by(id=int(webhookInputID)).first()
            if existingWebhookQuery is not None:
                existingWebhookQuery.name = webhookName
                existingWebhookQuery.endpointURL = webhookEndpoint
                existingWebhookQuery.requestHeader = webhookHeader
                existingWebhookQuery.requestPayload = webhookPayload
                existingWebhookQuery.requestType = webhookReqType
                existingWebhookQuery.requestTrigger = webhookTrigger

                emit('changeGlobalWebhookAck', {'webhookName': webhookName, 'requestURL': webhookEndpoint, 'requestHeader': webhookHeader, 'requestPayload': webhookPayload, 'requestType': webhookReqType, 'requestTrigger': webhookTrigger, 'requestID': existingWebhookQuery.id}, broadcast=False)
    db.session.commit()
    db.session.close()

@socketio.on('deleteGlobalWebhook')
def deleteGlobalWebhook(message):
    webhookID = int(message['webhookID'])
    webhookQuery = webhook.globalWebhook.query.filter_by(id=webhookID).first()

    if webhookQuery is not None:
        if current_user.has_role('Admin'):
            db.session.delete(webhookQuery)
            db.session.commit()
    db.session.close()

# Start App Initiation
try:
    init_db_values()

except Exception as e:
    print(e)
mail = Mail(app)
newLog("0", "OSP Started Up Successfully - version: " + str(version))

if __name__ == '__main__':
    app.jinja_env.auto_reload = False
    app.config['TEMPLATES_AUTO_RELOAD'] = False
    socketio.run(app)
