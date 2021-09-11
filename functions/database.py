import os
import json
import subprocess
import uuid

from flask import flash
import flask_migrate

from globals import globalvars

from classes.shared import db
from classes import settings
from classes import dbVersion
from classes import topics
from classes import Channel
from classes import RecordedVideo
from classes import Sec

from functions import system
from functions import cachedDbCalls

from conf import config

def checkDefaults(user_datastore):
    # Setup Default User Roles
    user_datastore.find_or_create_role(name='Admin', description='Administrator', default=False)
    user_datastore.find_or_create_role(name='User', description='User', default=True)
    user_datastore.find_or_create_role(name='Streamer', description='Streamer', default=False)
    user_datastore.find_or_create_role(name='Recorder', description='Recorder', default=False)
    user_datastore.find_or_create_role(name='Uploader', description='Uploader', default=False)

    print({"level": "info", "message": "Setting Default Topics"})
    topicList = [("Other", "None")]
    for topic in topicList:
        existingTopic = topics.topics.query.filter_by(name=topic[0]).first()
        if existingTopic is None:
            newTopic = topics.topics(topic[0], topic[1])
            db.session.add(newTopic)
    db.session.commit()
    return True

def dbFixes():
    sysSettings = settings.settings.query.first()

    print({"level": "info", "message": "Performing DB Sanity Check"})
    # Set/Update the system version attribute
    if sysSettings.version is None or sysSettings.version != globalvars.version:
        sysSettings.version = globalvars.version
        db.session.commit()
    # Sets the Default Theme is None is Set - Usual Cause is Moving from Alpha to Beta
    if sysSettings.systemTheme is None or sysSettings.systemTheme == "Default":
        sysSettings.systemTheme = "Defaultv2"
        db.session.commit()
    if sysSettings.siteProtocol is None:
        sysSettings.siteProtocol = "http://"
        db.session.commit()
    if sysSettings.version == "None":
        sysSettings.version = globalvars.version
        db.session.commit()
    if sysSettings.systemLogo is None:
        sysSettings.systemLogo = "/static/img/logo.png"
        db.session.commit()
    # Sets allowComments to False if None is Set - Usual Cause is moving from Alpha to Beta
    if sysSettings.allowComments is None:
        sysSettings.allowComments = False
        db.session.commit()
    # Sets allowUploads to False if None is Set - Caused by Moving from Pre-Beta 2
    if sysSettings.allowUploads is None:
        sysSettings.allowUploads = False
        db.session.commit()
    # Sets Blank Server Message to Prevent Crash if set to None
    if sysSettings.serverMessage is None:
        sysSettings.serverMessage = ""
        db.session.commit()
    # Sets Protection System Setting if None Exists:
    if sysSettings.protectionEnabled is None:
        sysSettings.protectionEnabled = True
        db.session.commit()
    # Sets Clip Length to Infinity on Upgraded Installs
    if sysSettings.maxClipLength is None:
        sysSettings.maxClipLength = 301
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

    print({"level": "info", "message": "Checking for Null Default Roles"})
    # Query Null Default Roles and Set
    roleQuery = Sec.Role.query.filter_by(default=None).all()
    for role in roleQuery:
        if role.name == "User":
            role.default = True
        else:
            role.default = False
        db.session.commit()

    # Checks for local RTMP Server Authorization
    rtmpServers = settings.rtmpServer.query.filter_by(address="127.0.0.1").first()
    if rtmpServers is None:
        localRTMP = settings.rtmpServer("127.0.0.1")
        db.session.add(localRTMP)
        db.session.commit()

    print({"level": "info", "message": "Performing Additional DB Sanity Checks"})
    # Fix for Videos and Channels that were created before Publishing Option
    videoQuery = RecordedVideo.RecordedVideo.query.filter_by(published=None).all()
    for vid in videoQuery:
        vid.published = True
        db.session.commit()
    clipQuery = RecordedVideo.Clips.query.filter_by(published=None).all()
    for clip in clipQuery:
        clip.published = True
        db.session.commit()
    channelQuery = Channel.Channel.query.filter_by(autoPublish=None).all()
    for chan in channelQuery:
        chan.autoPublish = True
        db.session.commit()
    # Fixes for Channels that do not have the restream settings initialized
    channelQuery = Channel.Channel.query.filter_by(rtmpRestream=None).all()
    for chan in channelQuery:
        chan.rtmpRestream = False
        chan.rtmpRestreamDestination = ""
        db.session.commit()

    # Fixes for Server Settings not having a Server Message Title
    if sysSettings.serverMessageTitle is None:
        sysSettings.serverMessageTitle = "Server Message"
        db.session.commit()
    if sysSettings.restreamMaxBitrate is None:
        sysSettings.restreamMaxBitrate = 3500
        db.session.commit()

    # Fix for Edge Conf Build on Restart
    if sysSettings.buildEdgeOnRestart is None:
        sysSettings.buildEdgeOnRestart = True
        db.session.commit()

    # Fixes for Server Settings Missing the Main Page Sort Option
    if sysSettings.sortMainBy is None:
        sysSettings.sortMainBy = 0
        db.session.commit()

    # Check for Users with Auth Type not Sent
    userQuery = Sec.User.query.filter_by(authType=None).all()
    for user in userQuery:
        user.authType = 0
        db.session.commit()

    userQuery = Sec.User.query.all()
    for user in userQuery:
        if " " in user.username:
            user.username = user.username.replace(" ", "_")
            db.session.commit()

    # Generate UUIDs for DB Items Missing
    userQuery = Sec.User.query.filter_by(uuid=None).all()
    for user in userQuery:
        user.uuid = str(uuid.uuid4())
        db.session.commit()
    videoQuery = RecordedVideo.RecordedVideo.query.filter_by(uuid=None).all()
    for vid in videoQuery:
        vid.uuid = str(uuid.uuid4())
        db.session.commit()
    clipQuery = RecordedVideo.Clips.query.filter_by(uuid=None).all()
    for clip in clipQuery:
        clip.uuid = str(uuid.uuid4())
        db.session.commit()

    # Generate XMPP Token for Users Missing
    userQuery = Sec.User.query.filter_by(xmppToken=None).all()
    for user in userQuery:
        user.xmppToken = str(os.urandom(32).hex())
        db.session.commit()

    # Generate XMPP Token for Channels Missing
    channelQuery = Channel.Channel.query.filter_by(xmppToken=None).all()
    for channel in channelQuery:
        channel.xmppToken = str(os.urandom(32).hex())
        db.session.commit()

    # Clear Any Localhost Guest UUIDs from the DB due to coding pre 0.8.6
    guestQuery = Sec.Guest.query.filter_by(last_active_ip="127.0.0.1").all()
    for guest in guestQuery:
        db.session.delete(guest)
    db.session.commit()

    # Check Existing RTMP Servers missing Hide Flag
    rtmpQuery = settings.rtmpServer.query.filter_by(hide=None).update(dict(hide=False))
    db.session.commit()


    return True

def init(app, user_datastore):
    db.create_all()

    print({"level": "info", "message": "Checking Flask-Migrate DB Version"})
    # Logic to Check the DB Version
    dbVersionQuery = dbVersion.dbVersion.query.first()

    if dbVersionQuery is None:
        newDBVersion = dbVersion.dbVersion(globalvars.appDBVersion)
        db.session.add(newDBVersion)
        db.session.commit()
        with app.app_context():
            migrate_db = flask_migrate.migrate()
            print(migrate_db)
            upgrade_db = flask_migrate.upgrade()
            print(upgrade_db)

    elif dbVersionQuery.version != globalvars.appDBVersion:
        dbVersionQuery.version = globalvars.appDBVersion
        db.session.commit()
        pass

    print({"level": "info", "message": "Setting up Default Roles"})
    # Performs Checks of Default Values for OSP
    checkDefaults(user_datastore)

    print({"level": "info", "message": "Querying Default System Settings"})
    # Note: for a freshly installed system, sysSettings is None!
    sysSettings = cachedDbCalls.getSystemSettings()

    if sysSettings is not None:

        print({"level": "info", "message": "Performing DB Checks and Fixes"})
        # Analyzes Known DB Issues and Corrects Them (Typically After a Migration)
        dbFixes()

        print({"level": "info", "message": "Reloading System Settings"})
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
        app.config['SECURITY_FORGOT_PASSWORD_TEMPLATE'] = 'security/forgot_password.html'
        app.config['SECURITY_LOGIN_USER_TEMPLATE'] = 'security/login_user.html'
        app.config['SECURITY_REGISTER_USER_TEMPLATE'] = 'security/register_user.html'
        app.config['SECURITY_SEND_CONFIRMATION_TEMPLATE'] = 'security/send_confirmation.html'
        app.config['SECURITY_RESET_PASSWORD_TEMPLATE'] = 'security/reset_password.html'
        app.config['SECURITY_EMAIL_SUBJECT_PASSWORD_RESET'] = sysSettings.siteName + " - Password Reset Request"
        app.config['SECURITY_EMAIL_SUBJECT_REGISTER'] = sysSettings.siteName + " - Welcome!"
        app.config['SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE'] = sysSettings.siteName + " - Password Reset Notification"
        app.config['SECURITY_EMAIL_SUBJECT_CONFIRM'] = sysSettings.siteName + " - Email Confirmation Request"

        print({"level": "info", "message": "Database Initialization Completed"})

        return True
