import os
import json
import subprocess
import uuid

from flask import flash
from flask_migrate import migrate, upgrade

from globals import globalvars

from classes.shared import db
from classes import settings
from classes import dbVersion
from classes import topics
from classes import Channel
from classes import RecordedVideo
from classes import Sec

from functions import system

from conf import config

def init(app, user_datastore):
    db.create_all()

    # Logic to Check the DB Version
    dbVersionQuery = dbVersion.dbVersion.query.first()

    if dbVersionQuery is None:
        newDBVersion = dbVersion.dbVersion(globalvars.appDBVersion)
        db.session.add(newDBVersion)
        db.session.commit()
        with app.app_context():
            migrate_db = migrate()
            print(migrate_db)
            upgrade_db = upgrade()
            print(upgrade_db)

    elif dbVersionQuery.version != globalvars.appDBVersion:
        dbVersionQuery.version = globalvars.appDBVersion
        db.session.commit()
        pass

    # Setup Default User Roles
    user_datastore.find_or_create_role(name='Admin', description='Administrator')
    user_datastore.find_or_create_role(name='User', description='User')
    user_datastore.find_or_create_role(name='Streamer', description='Streamer')
    user_datastore.find_or_create_role(name='Recorder', description='Recorder')
    user_datastore.find_or_create_role(name='Uploader', description='Uploader')

    topicList = [("Other","None")]
    for topic in topicList:
        existingTopic = topics.topics.query.filter_by(name=topic[0]).first()
        if existingTopic is None:
            newTopic = topics.topics(topic[0], topic[1])
            db.session.add(newTopic)
    db.session.commit()

    # Note: for a freshly installed system, sysSettings is None!
    sysSettings = settings.settings.query.first()

    if sysSettings is not None:
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

        # Fix for Beta 6 Switch from Fake Clips to real clips
        clipQuery = RecordedVideo.Clips.query.filter_by(videoLocation=None).all()
        videos_root = globalvars.videoRoot + 'videos/'
        for clip in clipQuery:
            originalVideo = videos_root + clip.recordedVideo.videoLocation
            clipVideoLocation = clip.recordedVideo.channel.channelLoc + '/clips/' + 'clip-' + str(clip.id) + ".mp4"
            fullvideoLocation = videos_root + clipVideoLocation
            clip.videoLocation = clipVideoLocation
            clipVideo = subprocess.run(['ffmpeg', '-ss', str(clip.startTime), '-i', originalVideo, '-c', 'copy', '-t', str(clip.length), '-avoid_negative_ts', '1', fullvideoLocation])
            db.session.commmit()

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

        # Fixes for Server Settings Missing the Main Page Sort Option
        if sysSettings.sortMainBy is None:
            sysSettings.sortMainBy = 0
            db.session.commit()

        # Check for Users with Auth Type not Sent
        userQuery = Sec.User.query.filter_by(authType=None).all()
        for user in userQuery:
            user.authType = 0
            db.session.commit()

        # Create the stream-thumb directory if it does not exist
        if not os.path.isdir(app.config['WEB_ROOT'] + "stream-thumb"):
            try:
                os.mkdir(app.config['WEB_ROOT'] + "stream-thumb")
            except OSError:
                flash("Unable to create <web-root>/stream-thumb", "error")

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

        # Initialize the OSP Edge Configuration - Mostly for Docker
        try:
            system.rebuildOSPEdgeConf()
        except:
            print("Error Rebuilding Edge Config")

        # Import Theme Data into Theme Dictionary
        with open('templates/themes/' + sysSettings.systemTheme +'/theme.json') as f:

            globalvars.themeData = json.load(f)

        # Initialize the Topic Cache
        topicQuery = topics.topics.query.all()
        for topic in topicQuery:
            globalvars.topicCache[topic.id] = topic.name

        ## Begin DB UTF8MB4 Fixes To Convert The DB if Needed
        if config.dbLocation[:6] != "sqlite":
            try:
                dbEngine = db.engine
                dbConnection = dbEngine.connect()
                dbConnection.execute("ALTER DATABASE `%s` CHARACTER SET 'utf8mb4' COLLATE 'utf8mb4_unicode_ci'" % dbEngine.url.database)

                sql = "SELECT DISTINCT(table_name) FROM information_schema.columns WHERE table_schema = '%s'" % dbEngine.url.database

                results = dbConnection.execute(sql)
                for row in results:
                    sql = "ALTER TABLE `%s` convert to character set DEFAULT COLLATE DEFAULT" % (row[0])
                    db.Connection.execute(sql)
                db.close()
            except:
                pass
        ## End DB UT8MB4 Fixes