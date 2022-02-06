import os
import datetime
import json
import shutil
import uuid
import socket
import xmltodict
import git
import re
import psutil
import pytz

import requests
from flask import request, flash, render_template, redirect, url_for, Blueprint, current_app, Response, session, abort
from flask_security import Security, SQLAlchemyUserDatastore, current_user, login_required, roles_required, logout_user
from flask_security.utils import hash_password
from flask_mail import Mail
from sqlalchemy.sql.expression import func

from werkzeug.utils import secure_filename

from classes.shared import db, email, oauth
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
from classes import stickers
from classes import panel
from classes.shared import cache

from functions import system
from functions import themes
from functions import cachedDbCalls
from functions import securityFunc

from globals import globalvars

from app import user_datastore
from app import photos
from app import stickerUploads

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/user', methods=['POST', 'GET'])
@login_required
def user_page():
    if request.method == 'GET':
        # Checks Total Used Space
        userChannels = Channel.Channel.query.filter_by(owningUser=current_user.id).with_entities(Channel.Channel.channelLoc, Channel.Channel.channelName).all()
        socialNetworks = Sec.UserSocial.query.filter_by(userID=current_user.id).with_entities(Sec.UserSocial.id, Sec.UserSocial.socialType, Sec.UserSocial.url).all()

        totalSpaceUsed = 0
        channelUsage = []
        for chan in userChannels:
            try:
                videos_root = globalvars.videoRoot + 'videos/'
                channelLocation = videos_root + chan.channelLoc

                total_size = 0
                for dirpath, dirnames, filenames in os.walk(channelLocation):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        total_size += os.path.getsize(fp)
            except FileNotFoundError:
                total_size = 0
            channelUsage.append({'name': chan.channelName, 'usage': total_size})
            totalSpaceUsed = totalSpaceUsed + total_size

        return render_template(themes.checkOverride('userSettings.html'), totalSpaceUsed=totalSpaceUsed, channelUsage=channelUsage, socialNetworkList=socialNetworks)

    elif request.method == 'POST':

        biography = request.form['biography']
        current_user.biography = biography

        if current_user.authType == 0:
            password1 = request.form['password1']
            password2 = request.form['password2']
            if password1 != "":
                if password1 == password2:
                    newPassword = hash_password(password1)
                    current_user.password = newPassword
                    system.newLog(1, "User Password Changed - Username:" + current_user.username)
                    flash("Password Changed")
                else:
                    flash("Passwords Don't Match!")

        emailAddress = request.form['emailAddress']
        existingEmailQuery = Sec.User.query.filter_by(email=emailAddress).first()
        if existingEmailQuery is not None:
            if existingEmailQuery.id != current_user.id:
                # TODO Add Option to Merge Existing Account
                flash("An User Account exists with the same email address", "error")
                return redirect(url_for('.user_page'))
        current_user.email = emailAddress

        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename != '':
                oldImage = None

                if current_user.pictureLocation is not None:
                    oldImage = current_user.pictureLocation

                filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')
                current_user.pictureLocation = filename

                if oldImage is not None:
                    try:
                        os.remove(oldImage)
                    except OSError:
                        pass

        system.newLog(1, "User Info Updated - Username:" + current_user.username)
        db.session.commit()

    return redirect(url_for('.user_page'))


@settings_bp.route('/user/subscriptions')
@login_required
def subscription_page():
    channelSubList = subscriptions.channelSubs.query.filter_by(userID=current_user.id).with_entities(subscriptions.channelSubs.id, subscriptions.channelSubs.channelID).all()

    return render_template(themes.checkOverride('subscriptions.html'), channelSubList=channelSubList)


@settings_bp.route('/user/deleteSelf')
@login_required
def user_delete_own_account():
    """
    Endpoint to allow user to delete own account and all associated data.
    Not to be called directly without confirmation UI
    """
    securityFunc.delete_user(current_user.id)
    flash('Account and Associated Data Deleted', 'error')
    logout_user()
    return redirect(url_for("main_page"))


@settings_bp.route('/user/addInviteCode')
def user_addInviteCode():
    if 'inviteCode' in request.args:
        inviteCode = request.args.get("inviteCode")
        inviteCodeQuery = invites.inviteCode.query.filter_by(code=inviteCode).first()
        if inviteCodeQuery is not None:
            if inviteCodeQuery.isValid():
                # Add Check if User is Authenticated to Add Code
                if current_user.is_authenticated:
                    existingInviteQuery = invites.invitedViewer.query.filter_by(inviteCode=inviteCodeQuery.id,
                                                                                userID=current_user.id).first()
                    if existingInviteQuery is None:
                        if inviteCodeQuery.expiration is not None:
                            remainingDays = (inviteCodeQuery.expiration - datetime.datetime.utcnow()).days
                        else:
                            remainingDays = 0
                        newInvitedUser = invites.invitedViewer(current_user.id, inviteCodeQuery.channelID, remainingDays,
                                                               inviteCode=inviteCodeQuery.id)
                        inviteCodeQuery.uses = inviteCodeQuery.uses + 1
                        db.session.add(newInvitedUser)
                        db.session.commit()
                        system.newLog(3,
                                      "User Added Invite Code to Account - Username:" + current_user.username + " Channel ID #" + str(
                                          inviteCodeQuery.channelID))
                        flash("Added Invite Code to Channel", "success")
                        if 'redirectURL' in request.args:
                            return redirect(request.args.get("redirectURL"))
                    else:
                        flash("Invite Code Already Applied", "error")
                else:
                    if 'inviteCodes' not in session:
                        session['inviteCodes'] = []
                    if inviteCodeQuery.code not in session['inviteCodes']:
                        session['inviteCodes'].append(inviteCodeQuery.code)
                        inviteCodeQuery.uses = inviteCodeQuery.uses + 1
                        system.newLog(3, "User Added Invite Code to Account - Username:" + 'Guest' + '-' + session['guestUUID'] + " Channel ID #" + str(inviteCodeQuery.channelID))
                    else:
                        flash("Invite Code Already Applied", "error")
            else:
                if current_user.is_authenticated:
                    system.newLog(3, "User Attempted to add Expired Invite Code to Account - Username:" + current_user.username + " Channel ID #" + str(inviteCodeQuery.channelID))
                else:
                    system.newLog(3, "User Attempted to add Expired Invite Code to Account - Username:" + 'Guest' + '-' + session['guestUUID'] + " Channel ID #" + str(inviteCodeQuery.channelID))
                flash("Invite Code Expired", "error")
        else:
            flash("Invalid Invite Code", "error")
    return redirect(url_for('root.main_page'))


@settings_bp.route('/admin', methods=['POST', 'GET'])
@login_required
@roles_required('Admin')
def admin_page():
    videos_root = current_app.config['WEB_ROOT'] + 'videos/'
    sysSettings = cachedDbCalls.getSystemSettings()
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

                    system.newLog(1, "User " + current_user.username + " deleted Topic " + str(topicQuery.name))
                    db.session.delete(topicQuery)
                    db.session.commit()
                    cache.delete_memoized(cachedDbCalls.getAllTopics)

                    # Initialize the Topic Cache
                    topicQuery = cachedDbCalls.getAllTopics()
                    for topic in topicQuery:
                        globalvars.topicCache[topic.id] = topic.name

                    flash("Topic Deleted")
                    return redirect(url_for('.admin_page', page="topics"))

                elif setting == "users":
                    userID = int(request.args.get("userID"))
                    userQuery = Sec.User.query.filter_by(id=userID).first()

                    if userQuery is not None:

                        securityFunc.delete_user(userQuery.id)

                        flash("User " + str(userQuery.username) + " Deleted")

                        db.session.delete(userQuery)
                        db.session.commit()

                        return redirect(url_for('.admin_page', page="users"))

                elif setting == "userRole":
                    userID = int(request.args.get("userID"))
                    roleID = int(request.args.get("roleID"))

                    userQuery = Sec.User.query.filter_by(id=userID).first()
                    roleQuery = Sec.Role.query.filter_by(id=roleID).first()

                    if userQuery is not None and roleQuery is not None:
                        user_datastore.remove_role_from_user(userQuery, roleQuery.name)
                        db.session.commit()
                        system.newLog(1,
                                      "User " + current_user.username + " Removed Role " + roleQuery.name + " from User" + userQuery.username)
                        flash("Removed Role from User")

                    else:
                        flash("Invalid Role or User!")
                    return redirect(url_for('.admin_page', page="users"))

            elif action == "add":
                if setting == "userRole":
                    userID = int(request.args.get("userID"))
                    roleName = str(request.args.get("roleName"))

                    userQuery = Sec.User.query.filter_by(id=userID).first()
                    roleQuery = Sec.Role.query.filter_by(name=roleName).first()

                    if userQuery is not None and roleQuery is not None:
                        user_datastore.add_role_to_user(userQuery, roleQuery.name)
                        db.session.commit()
                        system.newLog(1,
                                      "User " + current_user.username + " Added Role " + roleQuery.name + " to User " + userQuery.username)
                        flash("Added Role to User")
                    else:
                        flash("Invalid Role or User!")
                    return redirect(url_for('.admin_page', page="users"))
            elif action == "toggleActive":
                if setting == "users":
                    userID = int(request.args.get("userID"))
                    userQuery = Sec.User.query.filter_by(id=userID).first()
                    if userQuery is not None:
                        if userQuery.active:
                            userQuery.active = False
                            system.newLog(1, "User " + current_user.username + " Disabled User " + userQuery.username)
                            flash("User Disabled")
                        else:
                            userQuery.active = True
                            system.newLog(1, "User " + current_user.username + " Enabled User " + userQuery.username)
                            flash("User Enabled")
                        db.session.commit()
                    return redirect(url_for('.admin_page', page="users"))

            return redirect(url_for('.admin_page'))

        page = None
        if request.args.get('page') is not None:
            page = str(request.args.get("page"))
        repoSHA = "N/A"
        remoteSHA = repoSHA
        branch = "Local Install"
        validGitRepo = False
        repo = None
        try:
            repo = git.Repo(search_parent_directories=True)
            validGitRepo = True
        except:
            pass

        if validGitRepo:
            try:
                remoteSHA = None
                if repo is not None:
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
        streamList = Stream.Stream.query.filter_by(active=True)\
            .with_entities(Stream.Stream.id, Stream.Stream.linkedChannel, Stream.Stream.streamName, Stream.Stream.topic,
                           Stream.Stream.currentViewers, Stream.Stream.startTimestamp, Stream.Stream.endTimeStamp).all()
        streamHistory = Stream.Stream.query.filter_by(active=False)\
            .with_entities(Stream.Stream.id, Stream.Stream.startTimestamp, Stream.Stream.endTimeStamp,
                           Stream.Stream.linkedChannel, Stream.Stream.streamName, Stream.Stream.totalViewers).all()
        topicsList = cachedDbCalls.getAllTopics()
        rtmpServers = settings.rtmpServer.query.all()
        edgeNodes = settings.edgeStreamer.query.all()

        defaultRoles = {}
        for role in roleList:
            defaultRoles[role.name] = role.default

        # 30 Days Viewer Stats
        viewersTotal = 0

        # Create List of 30 Day Viewer Stats
        statsViewsLiveDay = db.session.query(func.date(views.views.date), func.count(views.views.id)).filter(
            views.views.viewType == 0).filter(
            views.views.date > (datetime.datetime.utcnow() - datetime.timedelta(days=30))).group_by(
            func.date(views.views.date)).all()
        statsViewsLiveDayArray = []
        for entry in statsViewsLiveDay:
            viewersTotal = viewersTotal + entry[1]
            statsViewsLiveDayArray.append({'t': (entry[0]), 'y': entry[1]})

        statsViewsRecordedDay = db.session.query(func.date(views.views.date), func.count(views.views.id)).filter(
            views.views.viewType == 1).filter(
            views.views.date > (datetime.datetime.utcnow() - datetime.timedelta(days=30))).group_by(
            func.date(views.views.date)).all()
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

        try:
            nginxStatDataRequest = requests.get('http://127.0.0.1:9000/stats')
            nginxStatData = (json.loads(json.dumps(xmltodict.parse(nginxStatDataRequest.text))))
        except:
            nginxStatData = None
        globalWebhookQuery = webhook.globalWebhook.query.all()

        themeList = []
        themeDirectorySearch = os.listdir("./templates/themes/")
        for theme in themeDirectorySearch:
            hasJSON = os.path.isfile("./templates/themes/" + theme + "/theme.json")
            if hasJSON:
                themeList.append(theme)

        logsList = logs.logs.query.order_by(logs.logs.timestamp.desc()).limit(250)

        oAuthProvidersList = settings.oAuthProvider.query.all()

        from app import ejabberd
        if ejabberd is None:
            flash("EJabberD is not connected and is required to access this page.  Contact your administrator", "error")
            return redirect(url_for("root.main_page"))

        # Generate CSV String for Banned Chat List
        bannedWordQuery = banList.chatBannedWords.query.all()
        bannedWordArray = []
        for bannedWord in bannedWordQuery:
            bannedWordArray.append(bannedWord.word)
        bannedWordArray = sorted(bannedWordArray)
        bannedWordString = ','.join(bannedWordArray)

        globalPanelList = panel.globalPanel.query.all()
        mainPagePanelMapping = panel.panelMapping.query.filter_by(pageName="root.main_page", panelType=0)
        mainPagePanelMappingSort = sorted(mainPagePanelMapping, key=lambda x: x.panelOrder)

        globalStickers = stickers.stickers.query.filter_by(channelID=None).all()

        system.newLog(1, "User " + current_user.username + " Accessed Admin Interface")

        from classes.shared import celery

        nodes = celery.control.inspect(['celery@osp'])
        scheduled = nodes.scheduled()
        active = nodes.active()
        claimed = nodes.reserved()
        schedulerList = {'nodes': nodes, 'scheduled': scheduled, 'active': active, 'claimed': claimed}

        return render_template(themes.checkOverride('admin.html'), appDBVer=appDBVer, userList=userList,
                               roleList=roleList, channelList=channelList, streamList=streamList, streamHistory=streamHistory, topicsList=topicsList,
                               repoSHA=repoSHA, repoBranch=branch,
                               remoteSHA=remoteSHA, themeList=themeList, statsViewsDay=statsViewsDay,
                               viewersTotal=viewersTotal, currentViewers=currentViewers, nginxStatData=nginxStatData,
                               globalHooks=globalWebhookQuery, defaultRoleDict=defaultRoles,
                               logsList=logsList, edgeNodes=edgeNodes, rtmpServers=rtmpServers, oAuthProvidersList=oAuthProvidersList,
                               ejabberdStatus=ejabberd, bannedWords=bannedWordString, globalStickers=globalStickers, page=page, timeZoneOptions=pytz.all_timezones,
                               schedulerList=schedulerList, globalPanelList=globalPanelList, mainPagePanelMapping=mainPagePanelMappingSort)
    elif request.method == 'POST':

        settingType = request.form['settingType']

        if settingType == "system":

            sysSettings = settings.settings.query.first()

            serverName = request.form['serverName']
            serverProtocol = request.form['siteProtocol']
            serverAddress = request.form['serverAddress']
            smtpSendAs = request.form['smtpSendAs']
            smtpAddress = request.form['smtpAddress']
            smtpPort = request.form['smtpPort']
            smtpUser = request.form['smtpUser']
            smtpPassword = request.form['smtpPassword']
            serverMessageTitle = request.form['serverMessageTitle']
            serverMessage = request.form['serverMessage']
            theme = request.form['theme']

            restreamMaxBitrate = request.form['restreamMaxBitrate']
            clipMaxLength = request.form['maxClipLength']

            recordSelect = False
            uploadSelect = False
            adaptiveStreaming = False
            showEmptyTables = False
            allowComments = False
            smtpTLS = False
            smtpSSL = False
            buildEdgeOnRestart = False
            protectionEnabled = False
            maintenanceMode = False

            # OSP Proxy Settings
            if 'ospProxyFQDN' in request.form:
                ospProxyFQDNForm = request.form['ospProxyFQDN']
                ospProxyFQDNForm = ospProxyFQDNForm.lower()
                ospProxyFQDNForm = ospProxyFQDNForm.replace('http://', '')
                ospProxyFQDNForm = ospProxyFQDNForm.replace('https://', '')
                if ospProxyFQDNForm.strip() == '':
                    ospProxyFQDN = None
                else:
                    ospProxyFQDN = ospProxyFQDNForm
                sysSettings.proxyFQDN = ospProxyFQDN

            if 'buildEdgeOnRestartSelect' in request.form:
                buildEdgeOnRestart = True

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

            if 'enableProtection' in request.form:
                protectionEnabled = True
            if 'maintenanceMode' in request.form:
                maintenanceMode = True

            if 'bannedChatWords' in request.form:
                bannedWordListString = request.form['bannedChatWords']
                bannedWordList = bannedWordListString.split(',')
                existingWordList = banList.chatBannedWords.query.all()
                for currentWord in existingWordList:
                    if currentWord.word not in bannedWordList:
                        db.session.delete(currentWord)
                    else:
                        bannedWordList.remove(currentWord.word)
                db.session.commit()
                for currentWord in bannedWordList:
                    newWord = banList.chatBannedWords(currentWord)
                    db.session.add(newWord)
                    db.session.commit()

            if 'termsSettings' in request.form:
                sysSettings.terms = request.form['termSettings']
            if 'privacySettings' in request.form:
                sysSettings.privacy = request.form['privacySettings']

            systemLogo = None
            if 'photo' in request.files:
                file = request.files['photo']
                if file.filename != '':
                    filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')
                    systemLogo = "/images/" + filename
                    themes.faviconGenerator(globalvars.videoRoot + 'images/' + filename)

            #validAddress = system.formatSiteAddress(serverAddress)
            #try:
            #    externalIP = socket.gethostbyname(validAddress)
            #except socket.gaierror:
            #    flash("Invalid Server Address/IP", "error")
            #    return redirect(url_for(".admin_page", page="settings"))

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
            if 'mainPageSort' in request.form:
                sysSettings.sortMainBy = int(request.form['mainPageSort'])
            if 'limitMaxChannels' in request.form:
                sysSettings.limitMaxChannels = int(request.form['limitMaxChannels'])
            if 'maxVideoRetention' in request.form:
                sysSettings.maxVideoRetention = int(request.form['maxVideoRetention'])
            # Check enableRTMPRestream - Workaround to pre 0.9.x themes, by checking for the existance of 'mainPageSort' which does not exist in >= 0.9.x
            if 'enableRTMPRestream' in request.form:
                sysSettings.allowRestream = True
            elif 'mainPageSort' not in request.form:
                sysSettings.allowRestream = False
            if 'serverTimeZone' in request.form:
                sysSettings.serverTimeZone = request.form['serverTimeZone']
            else:
                sysSettings.serverTimeZone = "UTC"
            sysSettings.serverMessageTitle = serverMessageTitle
            sysSettings.serverMessage = serverMessage
            sysSettings.protectionEnabled = protectionEnabled
            sysSettings.restreamMaxBitrate = int(restreamMaxBitrate)
            sysSettings.maintenanceMode = maintenanceMode
            sysSettings.maxClipLength = int(clipMaxLength)
            sysSettings.buildEdgeOnRestart = buildEdgeOnRestart

            if systemLogo is not None:
                sysSettings.systemLogo = systemLogo

            db.session.commit()

            cache.delete_memoized(cachedDbCalls.getSystemSettings)
            sysSettings = cachedDbCalls.getSystemSettings()

            current_app.config.update(
                SERVER_NAME=None,
                SECURITY_EMAIL_SENDER=sysSettings.smtpSendAs,
                MAIL_DEFAULT_SENDER=sysSettings.smtpSendAs,
                MAIL_SERVER=sysSettings.smtpAddress,
                MAIL_PORT=sysSettings.smtpPort,
                MAIL_USE_SSL=sysSettings.smtpSSL,
                MAIL_USE_TLS=sysSettings.smtpTLS,
                MAIL_USERNAME=sysSettings.smtpUsername,
                MAIL_PASSWORD=sysSettings.smtpPassword,
                SECURITY_EMAIL_SUBJECT_PASSWORD_RESET=sysSettings.siteName + " - Password Reset Request",
                SECURITY_EMAIL_SUBJECT_REGISTER=sysSettings.siteName + " - Welcome!",
                SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE=sysSettings.siteName + " - Password Reset Notification",
                SECURITY_EMAIL_SUBJECT_CONFIRM=sysSettings.siteName + " - Email Confirmation Request",
                SECURITY_FORGOT_PASSWORD_TEMPLATE='security/forgot_password.html',
                SECURITY_LOGIN_USER_TEMPLATE='security/login_user.html',
                SECURITY_REGISTER_USER_TEMPLATE='security/register_user.html',
                SECURITY_RESET_PASSWORD_TEMPLATE='security/reset_password.html',
                SECURITY_SEND_CONFIRMATION_TEMPLATE='security/send_confirmation.html')

            # ReInitialize Flask-Security
            #security = Security(current_app, user_datastore, register_form=Sec.ExtendedRegisterForm, confirm_register_form=Sec.ExtendedConfirmRegisterForm, login_form=Sec.OSPLoginForm)

            email = Mail()
            email.init_app(current_app)
            email.app = current_app

            themeList = []
            themeDirectorySearch = os.listdir("./templates/themes/")
            for theme in themeDirectorySearch:
                hasJSON = os.path.isfile("./templates/themes/" + theme + "/theme.json")
                if hasJSON:
                    themeList.append(theme)

            # Import Theme Data into Theme Dictionary
            with open('templates/themes/' + sysSettings.systemTheme + '/theme.json') as f:

                globalvars.themeData = json.load(f)

            system.newLog(1, "User " + current_user.username + " altered System Settings")

            return redirect(url_for('.admin_page', page="settings"))

        elif settingType == "newSticker":
            if 'stickerName' in request.form:
                stickerName = request.form['stickerName']
                existingStickerNameQuery = stickers.stickers.query.filter_by(name=stickerName).first()
                if existingStickerNameQuery is None:
                    if 'stickerUpload' in request.files:
                        file = request.files['stickerUpload']
                        if file.filename != '':
                            fileName = stickerUploads.save(request.files['stickerUpload'], name=stickerName + '.', folder='stickers')
                            fileName = fileName.replace('stickers/',"")
                            newSticker = stickers.stickers(stickerName, fileName)
                            db.session.add(newSticker)
                            db.session.commit()
                else:
                    flash("Sticker Name Already Exists","error")
            else:
                flash("Sticker Name Missing", "error")
            return redirect(url_for('.admin_page', page="stickers"))

        elif settingType == "topics":

            if 'topicID' in request.form and request.form['topicID'] != 'None':
                topicID = int(request.form['topicID'])
                topicName = request.form['name']

                topicQuery = topics.topics.query.filter_by(id=topicID).first()

                if topicQuery is not None:
                    cache.delete_memoized(cachedDbCalls.getAllTopics)

                    topicQuery.name = topicName

                    if 'photo' in request.files:
                        file = request.files['photo']
                        if file.filename != '':
                            oldImage = None

                            if topicQuery.iconClass is not None:
                                oldImage = topicQuery.iconClass

                            filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')
                            topicQuery.iconClass = filename

                            if oldImage is not None:
                                try:
                                    os.remove(oldImage)
                                except OSError:
                                    pass
            else:
                topicName = request.form['name']
                cache.delete_memoized(cachedDbCalls.getAllTopics)

                topicImage = None
                if 'photo' in request.files:
                    file = request.files['photo']
                    if file.filename != '':
                        filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')
                        topicImage = filename

                newTopic = topics.topics(topicName, topicImage)
                db.session.add(newTopic)

            # Initialize the Topic Cache
            topicQuery = cachedDbCalls.getAllTopics()
            for topic in topicQuery:
                globalvars.topicCache[topic.id] = topic.name

            db.session.commit()
            return redirect(url_for('.admin_page', page="topics"))

        elif settingType == "rtmpServer":
            address = request.form['address']

            existingServer = settings.rtmpServer.query.filter_by(address=address).first()

            if existingServer is None:
                newServer = settings.rtmpServer(address)
                db.session.add(newServer)
                db.session.commit()
                flash("Server Added", "success")
            else:
                flash("Server Already Exists","error")

            return redirect(url_for('.admin_page', page="osprtmp"))

        elif settingType == "edgeNode":
            address = request.form['address']
            port = request.form['edgePort']
            loadPct = request.form['edgeLoad']
            newEdge = settings.edgeStreamer(address, port, loadPct)

            try:
                edgeXML = requests.get("http://" + address + ":9000/stat").text
                edgeDict = xmltodict.parse(edgeXML)
                if "nginx_rtmp_version" in edgeDict['rtmp']:
                    newEdge.status = 1
                    db.session.add(newEdge)
                    db.session.commit()
            except:
                newEdge.status = 0
                db.session.add(newEdge)
                db.session.commit()

            return redirect(url_for('.admin_page', page="ospedge"))

        elif settingType == "oAuthProvider":
            oAuth_type = request.form['oAuthPreset']
            oAuth_name = request.form['oAuthName']
            oAuth_friendlyName = request.form['oAuthFriendlyName']
            oAuth_displayColor = request.form['oAuthColor']
            oAuth_client_id = request.form['oAuthClient_id']
            oAuth_client_secret = request.form['oAuthClient_secret']
            oAuth_access_token_url = None
            oAuth_access_token_params = None
            oAuth_authorize_url = None
            oAuth_authorize_params = None
            oAuth_api_base_url = None
            oAuth_client_kwargs = None
            oAuth_profile_endpoint = None
            oAuth_id = None
            oAuth_username = None
            oAuth_email = None

            # Apply Custom or Preset Settings for Providers
            if oAuth_type == "Custom":
                oAuth_access_token_url = request.form['oAuthAccess_token_url']
                oAuth_access_token_params = request.form['oAuthAccess_token_params']
                oAuth_authorize_url = request.form['oAuthAuthorize_url']
                oAuth_authorize_params = request.form['oAuthAuthorize_params']
                oAuth_api_base_url = request.form['oAuthApi_base_url']
                oAuth_client_kwargs = request.form['oAuthClient_kwargs']
                oAuth_profile_endpoint = request.form['oAuthProfile_endpoint']
                oAuth_id = request.form['oAuthIDValue']
                oAuth_username = request.form['oAuthUsername']
                oAuth_email = request.form['oAuthEmail']
                if oAuth_access_token_params == '':
                    oAuth_access_token_params = None
                if oAuth_authorize_params == '':
                    oAuth_authorize_params = None
                if oAuth_client_kwargs == '':
                    oAuth_client_kwargs = None

            elif oAuth_type == "Discord":
                oAuth_access_token_url = 'https://discordapp.com/api/oauth2/token'
                oAuth_authorize_url = 'https://discordapp.com/api/oauth2/authorize'
                oAuth_api_base_url = 'https://discordapp.com/api/'
                oAuth_client_kwargs = '{"scope":"identify email"}'
                oAuth_profile_endpoint = 'users/@me'
                oAuth_id = 'id'
                oAuth_username = 'username'
                oAuth_email = 'email'
            elif oAuth_type == "Reddit":
                oAuth_access_token_url = 'https://www.reddit.com/api/v1/access_token'
                oAuth_authorize_url = 'https://www.reddit.com/api/v1/authorize'
                oAuth_api_base_url = 'https://oauth.reddit.com/api/v1/'
                oAuth_client_kwargs = '{"scope":"identity"}'
                oAuth_profile_endpoint = 'me'
                oAuth_id = 'id'
                oAuth_username = 'name'
                oAuth_email = 'email'
            elif oAuth_type == "Facebook":
                oAuth_access_token_url = 'https://graph.facebook.com/v6.0/oauth/access_token'
                oAuth_authorize_url = 'https://graph.facebook.com/v6.0/oauth/authorize'
                oAuth_api_base_url = 'https://graph.facebook.com/v6.0/'
                oAuth_client_kwargs = '{"scope": "email public_profile"}'
                oAuth_profile_endpoint = 'me?fields=name,id,email'
                oAuth_id = 'id'
                oAuth_username = 'name'
                oAuth_email = 'email'

            if request.form['oAuthID'] == '':
                newOauthProvider = settings.oAuthProvider(oAuth_name, oAuth_type, oAuth_friendlyName, oAuth_displayColor, oAuth_client_id, oAuth_client_secret, oAuth_access_token_url, oAuth_authorize_url, oAuth_api_base_url, oAuth_profile_endpoint, oAuth_id, oAuth_username, oAuth_email)
                if oAuth_access_token_params is not None:
                    newOauthProvider.access_token_params = oAuth_access_token_params
                if oAuth_authorize_params is not None:
                    newOauthProvider.authorize_params = oAuth_authorize_params
                if oAuth_client_kwargs is not None:
                    newOauthProvider.client_kwargs = oAuth_client_kwargs

                db.session.add(newOauthProvider)
                db.session.commit()

                provider = settings.oAuthProvider.query.filter_by(name=oAuth_name).first()

                oauth.register(
                    name=provider.name,
                    client_id=provider.client_id,
                    client_secret=provider.client_secret,
                    access_token_url=provider.access_token_url,
                    access_token_params=provider.access_token_params if (provider.access_token_params != '' and provider.access_token_params is not None) else None,
                    authorize_url=provider.authorize_url,
                    authorize_params=provider.authorize_params if (provider.authorize_params != '' and provider.authorize_params is not None) else None,
                    api_base_url=provider.api_base_url,
                    client_kwargs=json.loads(provider.client_kwargs) if (provider.client_kwargs != '' and provider.client_kwargs is not None) else None,
                )

                flash("OAuth Provider Added", "success")

            else:
                existingOAuthID = request.form['oAuthID']
                oAuthQuery = settings.oAuthProvider.query.filter_by(id=int(existingOAuthID)).first()
                if oAuthQuery is not None:
                    oldOAuthName = oAuthQuery.name
                    oAuthQuery.preset_auth_type = oAuth_type
                    oAuthQuery.name = oAuth_name
                    oAuthQuery.friendlyName = oAuth_friendlyName
                    oAuthQuery.displayColor = oAuth_displayColor
                    oAuthQuery.client_id = oAuth_client_id
                    oAuthQuery.client_secret = oAuth_client_secret
                    oAuthQuery.access_token_url = oAuth_access_token_url
                    oAuthQuery.access_token_params = oAuth_access_token_params
                    oAuthQuery.authorize_url = oAuth_authorize_url
                    oAuthQuery.authorize_params = oAuth_authorize_params
                    oAuthQuery.api_base_url = oAuth_api_base_url
                    oAuthQuery.client_kwargs = oAuth_client_kwargs
                    oAuthQuery.profile_endpoint = oAuth_profile_endpoint
                    oAuthQuery.id_value = oAuth_id
                    oAuthQuery.username_value = oAuth_username
                    oAuthQuery.email_value = oAuth_email

                    db.session.commit()

                    userQuery = Sec.User.query.filter_by(oAuthProvider=oldOAuthName).all()
                    for user in userQuery:
                        user.oAuthProvider = oAuth_name
                    db.session.commit()

                    tokenQuery = Sec.OAuth2Token.query.filter_by(name=oldOAuthName).all()
                    for token in tokenQuery:
                        token.name = oAuth_name
                    db.session.commit()

                    provider = settings.oAuthProvider.query.filter_by(name=oAuth_name).first()

                    oauth.register(
                        name=provider.name,
                        overwrite=True,
                        client_id=provider.client_id,
                        client_secret=provider.client_secret,
                        access_token_url=provider.access_token_url,
                        access_token_params=provider.access_token_params if (provider.access_token_params != '' and provider.access_token_params is not None) else None,
                        authorize_url=provider.authorize_url,
                        authorize_params=provider.authorize_params if (provider.authorize_params != '' and provider.authorize_params is not None) else None,
                        api_base_url=provider.api_base_url,
                        client_kwargs=json.loads(provider.client_kwargs) if (provider.client_kwargs != '' and provider.client_kwargs is not None) else None,
                    )

                    flash("OAuth Provider Updated","success")
                else:
                    flash("OAuth Provider Does Not Exist", "error")

            return redirect(url_for('.admin_page', page="oauth"))

        elif settingType == "DeleteOAuthProvider":
            oAuthProvider = request.form['DeleteOAuthProviderID']

            oAuthProviderQuery = settings.oAuthProvider.query.filter_by(id=int(oAuthProvider)).first()
            if oAuthProvider is not None:
                userQuery = Sec.User.query.filter_by(oAuthProvider=oAuthProviderQuery.name, authType=1).all()
                count = 0
                for user in userQuery:
                    count = count + 1
                    user.authType = 0
                    user.oAuthProvider = ""
                    user.password = hash_password(str(uuid.uuid4()))
                    for token in user.oAuthToken:
                        db.session.delete(token)
                    db.session.commit()
                db.session.delete(oAuthProviderQuery)
                db.session.commit()
                flash("OAuth Provider Deleted - " + str(count) + " User(s) Converted to Local Users", "success")
            else:
                flash("Invalid OAuth Object","error")
            return redirect(url_for('.admin_page', page="oauth"))

        elif settingType == "newuser":

            password = request.form['password1']
            emailAddress = request.form['emailaddress']
            username = request.form['username']

            # Check for Existing Users
            existingUserQuery = Sec.User.query.filter_by(username=username).first()
            if existingUserQuery is not None:
                flash("A user already exists with this username","error")
                db.session.commit()
                return redirect(url_for('.admin_page', page="users"))

            existingUserQuery = Sec.User.query.filter_by(email=emailAddress).first()
            if existingUserQuery is not None:
                flash("A user already exists with this email address", "error")
                db.session.commit()
                return redirect(url_for('.admin_page', page="users"))

            passwordhash = hash_password(password)

            user_datastore.create_user(email=emailAddress, username=username, password=passwordhash)
            db.session.commit()

            user = Sec.User.query.filter_by(username=username).first()
            defaultRoleQuery = Sec.Role.query.filter_by(default=True).all()
            for role in defaultRoleQuery:
                user_datastore.add_role_to_user(user, role.name)
            user.authType = 0
            user.xmppToken = str(os.urandom(32).hex())
            user.uuid = str(uuid.uuid4())
            user.confirmed_at = datetime.datetime.utcnow()
            db.session.commit()
            return redirect(url_for('.admin_page', page="users"))

        elif settingType == "panel":
            panelName = request.form['panel-name']
            panelType = int(request.form['panel-type'])
            panelHeader = request.form['panel-header']
            panelContent = request.form['panel-content']
            globalPanelId = request.form['PanelId']

            panelOrder = 0
            if panelType != 0:
                if 'panel-order' in request.form:
                    panelOrder = int(request.form['panel-order'])

            if globalPanelId == "":
                newGlobalPanel = panel.globalPanel(panelName, panelType, panelHeader, panelOrder, panelContent)
                db.session.add(newGlobalPanel)
                db.session.commit()
            else:
                globalPanelId = int(globalPanelId)
                existingPanel = panel.globalPanel.query.filter_by(id=globalPanelId).first()
                if existingPanel is not None:
                    existingPanel.name = panelName
                    existingPanel.type = panelType
                    existingPanel.header = panelHeader
                    existingPanel.order = panelOrder
                    existingPanel.content = panelContent
                    cache.delete_memoized(cachedDbCalls.getGlobalPanel, globalPanelId)
                    db.session.commit()
            return redirect(url_for('.admin_page', page="settings"))

        return redirect(url_for('.admin_page'))

@settings_bp.route('/admin/create_test_task')
@login_required
@roles_required('Admin')
def createtestask():
    result = system.testCelery.apply_async(countdown=1)
    return str(result)

@settings_bp.route('/admin/rtmpstat/<node>')
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
        return data
    return abort(500)

@settings_bp.route('/channels', methods=['POST', 'GET'])
@login_required
@roles_required('Streamer')
def settings_channels_page():
    sysSettings = cachedDbCalls.getSystemSettings()

    videos_root = current_app.config['WEB_ROOT'] + 'videos/'

    if request.method == 'POST':
        requestType = None

        # Workaround check if we are now using a modal originally for Admin/Global
        if 'type' in request.form:
            requestType = request.form['type']
        elif 'settingType' in request.form:
            requestType = request.form['settingType']

        # Process New Stickers
        if requestType == "newSticker":
            if 'stickerChannelID' in request.form:
                channelQuery = Channel.Channel.query.filter_by(id=int(request.form['stickerChannelID']), owningUser=current_user.id).first()
                if channelQuery is not None:
                    if 'stickerName' in request.form:
                        stickerName = request.form['stickerName']
                        existingStickerNameQuery = stickers.stickers.query.filter_by(name=stickerName).first()
                        if existingStickerNameQuery is None:
                            if 'stickerUpload' in request.files:
                                file = request.files['stickerUpload']
                                if file.filename != '':
                                    fileName = stickerUploads.save(request.files['stickerUpload'], name=stickerName + '.', folder='stickers/' + channelQuery.channelLoc)
                                    fileName = fileName.replace('stickers/' + channelQuery.channelLoc + '/', "")
                                    newSticker = stickers.stickers(stickerName, fileName)
                                    newSticker.channelID = channelQuery.id
                                    db.session.add(newSticker)
                                    db.session.commit()
                                    flash("Sticker Added", "Success")
                        else:
                            flash("Sticker Name Already Exists", "Error")
                    else:
                        flash("Sticker Name Missing", "Error")
                else:
                    flash("Sticker Did Not Define Channel ID", "Error")
            return redirect(url_for('settings.settings_channels_page'))
        elif requestType == "panel":
            panelName = request.form['panel-name']
            panelType = int(request.form['panel-type'])
            panelHeader = request.form['panel-header']
            panelContent = request.form['panel-content']
            PanelId = request.form['PanelId']
            panelChannelId = int(request.form['PanelLocationId'])

            channelQuery = Channel.Channel.query.filter_by(id=panelChannelId, owningUser=current_user.id).first()
            if channelQuery is not None:

                panelOrder = 0
                if panelType != 0:
                    if 'panel-order' in request.form:
                        panelOrder = int(request.form['panel-order'])

                if PanelId == "":
                    newChannellPanel = panel.channelPanel(panelName, channelQuery.id, panelType, panelHeader, panelOrder, panelContent)
                    db.session.add(newChannellPanel)
                    db.session.commit()
                    flash("New Channel Panel Added", "Success")
                else:
                    existingPanel = panel.channelPanel.query.filter_by(id=PanelId, channelId=channelQuery.id).first()
                    if existingPanel is not None:
                        existingPanel.name = panelName
                        existingPanel.type = panelType
                        existingPanel.header = panelHeader
                        existingPanel.order = panelOrder
                        existingPanel.content = panelContent
                        cache.delete_memoized(cachedDbCalls.getChannelPanel, PanelId)
                        db.session.commit()
                        flash("Panel Updated", "Success")
                    else:
                        flash("Invalid Panel", "Error")
                return redirect(url_for('settings.settings_channels_page'))
            else:
                flash("Invalid Channel", "Error")
                return redirect(url_for('settings.settings_channels_page'))

        channelName = system.strip_html(request.form['channelName'])
        topic = request.form['channeltopic']
        description = system.strip_html(request.form['description'])

        record = False

        if 'recordSelect' in request.form and sysSettings.allowRecording is True:
            record = True

        autoPublish = False
        if 'publishSelect' in request.form:
            autoPublish = True

        chatEnabled = False

        if 'chatSelect' in request.form:
            chatEnabled = True

        allowComments = False

        if 'allowComments' in request.form:
            allowComments = True

        protection = False

        if 'channelProtection' in request.form:
            protection = True

        showHome = False

        if 'showHome' in request.form:
            showHome = True

        private = False

        if 'private' in request.form:
            private = True

        if requestType == 'new':
            # Check Maximum Channel Limit
            if sysSettings.limitMaxChannels != 0 and current_user.has_role('Admin') is False:
                channelCount = Channel.Channel.query.filter_by(owningUser=current_user.id).count()
                if channelCount >= sysSettings.limitMaxChannels:
                    flash("Maximum Number of Channels Allowed Reached - Limit: " + str(sysSettings.limitMaxChannels), "error")
                    db.session.commit()
                    redirect(url_for('.settings_channels_page'))

            newUUID = str(uuid.uuid4())

            newChannel = Channel.Channel(current_user.id, newUUID, channelName, topic, record, chatEnabled,
                                         allowComments, showHome, description)

            if 'photo' in request.files:
                file = request.files['photo']
                if file.filename != '':
                    filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')
                    newChannel.imageLocation = filename

            # Establish XMPP Channel
            from app import ejabberd
            ejabberd.create_room(newChannel.channelLoc, 'conference.' + sysSettings.siteAddress, sysSettings.siteAddress)
            ejabberd.set_room_affiliation(newChannel.channelLoc, 'conference.' + sysSettings.siteAddress, (current_user.uuid) + "@" + sysSettings.siteAddress, "owner")

            # Defautl values
            for key, value in globalvars.room_config.items():
                ejabberd.change_room_option(newChannel.channelLoc, 'conference.' + sysSettings.siteAddress, key, value)

            # Name and title
            ejabberd.change_room_option(newChannel.channelLoc, 'conference.' + sysSettings.siteAddress, 'title', newChannel.channelName)
            ejabberd.change_room_option(newChannel.channelLoc, 'conference.' + sysSettings.siteAddress, 'description', current_user.username + 's chat room for the channel "' + newChannel.channelName + '"')

            db.session.add(newChannel)
            db.session.commit()

        elif requestType == 'change':
            streamKey = request.form['streamKey']
            origStreamKey = request.form['origStreamKey']

            defaultstreamName = request.form['channelStreamName']

            #rtmpRestreamDestination = request.form['rtmpDestination']

            # TODO Validate ChatBG and chatAnimation

            requestedChannel = Channel.Channel.query.filter_by(streamKey=origStreamKey).first()

            if current_user.id == requestedChannel.owningUser:
                requestedChannel.channelName = channelName
                requestedChannel.streamKey = streamKey
                requestedChannel.topic = topic
                requestedChannel.record = record
                requestedChannel.chatEnabled = chatEnabled
                requestedChannel.allowComments = allowComments
                requestedChannel.showHome = showHome
                requestedChannel.description = description
                requestedChannel.protected = protection
                requestedChannel.defaultStreamName = defaultstreamName
                requestedChannel.autoPublish = autoPublish
                requestedChannel.private = private

                if 'channelTags' in request.form:
                    channelTagString = request.form['channelTags']
                    tagArray = system.parseTags(channelTagString)
                    existingTagArray = Channel.channel_tags.query.filter_by(channelID=requestedChannel.id).all()

                    for currentTag in existingTagArray:
                        if currentTag.name not in tagArray:
                            db.session.delete(currentTag)
                        else:
                            tagArray.remove(currentTag.name)
                    db.session.commit()
                    for currentTag in tagArray:
                        newTag = Channel.channel_tags(currentTag, requestedChannel.id, current_user.id)
                        db.session.add(newTag)
                        db.session.commit()

                vanityURL = None
                if 'vanityURL' in request.form:
                    requestedVanityURL = request.form['vanityURL']
                    requestedVanityURL = re.sub('[^A-Za-z0-9]+', '', requestedVanityURL)
                    if requestedVanityURL != '':
                        existingChannelQuery = Channel.Channel.query.filter_by(vanityURL=requestedVanityURL).first()
                        if existingChannelQuery is None or existingChannelQuery.id == requestedChannel.id:
                            vanityURL = requestedVanityURL
                        else:
                            flash("Short link not saved. Link with same name exists!", "error")

                requestedChannel.vanityURL = vanityURL

                from app import ejabberd
                if protection is True:
                    ejabberd.change_room_option(requestedChannel.channelLoc, 'conference.' + sysSettings.siteAddress, 'password_protected', 'true')
                    ejabberd.change_room_option(requestedChannel.channelLoc, 'conference.' + sysSettings.siteAddress, 'password', requestedChannel.xmppToken)
                else:
                    ejabberd.change_room_option(requestedChannel.channelLoc, 'conference.' + sysSettings.siteAddress, 'password', '')
                    ejabberd.change_room_option(requestedChannel.channelLoc, 'conference.' + sysSettings.siteAddress, 'password_protected', 'false')

                if 'photo' in request.files:
                    file = request.files['photo']
                    if file.filename != '':
                        oldImage = None

                        if requestedChannel.imageLocation is not None:
                            oldImage = requestedChannel.imageLocation

                        filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')
                        requestedChannel.imageLocation = filename

                        if oldImage is not None:
                            try:
                                os.remove(oldImage)
                            except OSError:
                                pass

                if 'offlinephoto' in request.files:
                    file = request.files['offlinephoto']
                    if file.filename != '':
                        oldImage = None

                        if requestedChannel.offlineImageLocation is not None:
                            oldImage = requestedChannel.offlineImageLocation

                        filename = photos.save(request.files['offlinephoto'], name=str(uuid.uuid4()) + '.')
                        requestedChannel.offlineImageLocation = filename

                        if oldImage is not None:
                            try:
                                os.remove(oldImage)
                            except OSError:
                                pass

                # Invalidate Channel Cache
                cachedDbCalls.invalidateChannelCache(requestedChannel.id)

                flash("Channel Saved")
                db.session.commit()
            else:
                flash("Invalid Change Attempt", "Error")
            redirect(url_for('.settings_channels_page'))

    topicList = topics.topics.query.all()
    user_channels = Channel.Channel.query.filter_by(owningUser=current_user.id).all()

    activeRTMPQuery = settings.rtmpServer.query.filter_by(active=True, hide=False).all()
    activeRTMPList = []
    for server in activeRTMPQuery:
        address = server.address
        if address == "127.0.0.1" or address == "localhost":
            address = sysSettings.siteAddress
        if address not in activeRTMPList:
            activeRTMPList.append(address)

    # Get xmpp room options
    from app import ejabberd
    channelRooms = {}
    channelMods = {}
    for chan in user_channels:
        try:
            xmppQuery = ejabberd.get_room_options(chan.channelLoc, 'conference.' + sysSettings.siteAddress)
        except AttributeError:
            # If Channel Doesn't Exist in ejabberd, Create
            ejabberd.create_room(chan.channelLoc, 'conference.' + sysSettings.siteAddress, sysSettings.siteAddress)
            ejabberd.set_room_affiliation(chan.channelLoc, 'conference.' + sysSettings.siteAddress, (current_user.uuid) + "@" + sysSettings.siteAddress, "owner")

            # Default values
            for key, value in globalvars.room_config.items():
                ejabberd.change_room_option(chan.channelLoc, 'conference.' + sysSettings.siteAddress, key, value)

            # Name and title
            ejabberd.change_room_option(chan.channelLoc, 'conference.' + sysSettings.siteAddress, 'title', chan.channelName)
            ejabberd.change_room_option(chan.channelLoc, 'conference.' + sysSettings.siteAddress, 'description', current_user.username + 's chat room for the channel "' + chan.channelName + '"')
            xmppQuery = ejabberd.get_room_options(chan.channelLoc, 'conference.' + sysSettings.siteAddress)
        except:
            # Try again if request causes strange "http.client.CannotSendRequest: Request-sent" Error
            return redirect(url_for("settings.settings_channels_page"))
        channelOptionsDict = {}
        if 'options' in xmppQuery:
            for option in xmppQuery['options']:
                key = None
                value = None
                for entry in option['option']:
                    if 'name' in entry:
                            key = entry['name']
                    elif 'value' in entry:
                            value = entry['value']
                if key is not None and value is not None:
                    channelOptionsDict[key] = value
        channelRooms[chan.channelLoc] = channelOptionsDict

        # Get room affiliations
        xmppQuery = ejabberd.get_room_affiliations(chan.channelLoc, 'conference.' + sysSettings.siteAddress)

        affiliationList = []
        for affiliation in xmppQuery['affiliations']:
            user = {}
            for entry in affiliation['affiliation']:
                for key, value in entry.items():
                    user[key] = value
            affiliationList.append(user)
        
        channelModList = []
        for user in affiliationList:
            if user['affiliation'] == "admin":
                channelModList.append(user['username'] + "@" + user['domain'])
        channelMods[chan.channelLoc] = channelModList

    # Calculate Channel Views by Date based on Video or Live Views and Generate Chanel Panel Ordering
    user_channels_stats = {}
    channelPanelOrder = {}
    for channel in user_channels:

        # 30 Days Viewer Stats
        viewersTotal = 0

        statsViewsLiveDay = db.session.query(func.date(views.views.date), func.count(views.views.id)).filter(
            views.views.viewType == 0).filter(views.views.itemID == channel.id).filter(
            views.views.date > (datetime.datetime.utcnow() - datetime.timedelta(days=30))).group_by(
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
                views.views.date > (datetime.datetime.utcnow() - datetime.timedelta(days=30))).group_by(
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

        channelPanelOrderMappingQuery = panel.panelMapping.query.filter_by(panelType=2, panelLocationId=channel.id).all()
        ChannelPanelOrderArray = []
        for panelEntry in channelPanelOrderMappingQuery:
            ChannelPanelOrderArray.append(panelEntry)
        channelPanelOrder[channel.id] = sorted(ChannelPanelOrderArray, key=lambda x: x.panelOrder)

    return render_template(themes.checkOverride('user_channels.html'), channels=user_channels, topics=topicList, channelRooms=channelRooms, channelMods=channelMods,
                           viewStats=user_channels_stats, rtmpList=activeRTMPList, channelPanelMapping=channelPanelOrder)


@settings_bp.route('/channels/chat', methods=['POST', 'GET'])
@login_required
@roles_required('Streamer')
def settings_channels_chat_page():
    sysSettings = cachedDbCalls.getSystemSettings()

    if request.method == 'POST':
        from app import ejabberd
        channelLoc = system.strip_html(request.form['channelLoc'])
        channelQuery = Channel.Channel.query.filter_by(channelLoc=request.form['channelLoc']).first()
        if channelQuery is not None and current_user.id == channelQuery.owningUser:
            roomTitle = request.form['roomTitle']
            roomDescr = system.strip_html(request.form['roomDescr'])
            ejabberd.change_room_option(channelLoc, 'conference.' + sysSettings.siteAddress, "title", roomTitle)
            ejabberd.change_room_option(channelLoc, 'conference.' + sysSettings.siteAddress, "description", roomDescr)

            if 'moderatedSelect' in request.form:
                ejabberd.change_room_option(channelLoc, 'conference.' + sysSettings.siteAddress, "moderated", "true")
            else:
                ejabberd.change_room_option(channelLoc, 'conference.' + sysSettings.siteAddress, "moderated", "false")

            if 'allowGuests' in request.form:
                ejabberd.change_room_option(channelLoc, 'conference.' + sysSettings.siteAddress, "members_only", "false")
            else:
                ejabberd.change_room_option(channelLoc, 'conference.' + sysSettings.siteAddress, "members_only", "true")

            if 'allowGuestsChat' in request.form:
                ejabberd.change_room_option(channelLoc, 'conference.' + sysSettings.siteAddress, "members_by_default", "true")
            else:
                ejabberd.change_room_option(channelLoc, 'conference.' + sysSettings.siteAddress, "members_by_default", "false")
            if 'allowGuestsNickChange' in request.form:
                channelQuery.allowGuestNickChange = True
            else:
                channelQuery.allowGuestNickChange = False
            db.session.commit()

    return redirect(url_for('settings.settings_channels_page'))


@settings_bp.route('/api', methods=['GET'])
@login_required
@roles_required('Streamer')
def settings_apikeys_page():
    apiKeyQuery = apikey.apikey.query.filter_by(userID=current_user.id).all()
    return render_template(themes.checkOverride('apikeys.html'), apikeys=apiKeyQuery)


@settings_bp.route('/api/<string:action>', methods=['POST'])
@login_required
@roles_required('Streamer')
def settings_apikeys_post_page(action):
    if action == "new":
        validKeyTypes = [1,2]
        validRequest = False
        if 'keyType' in request.form:
            requestedKeyType = int(request.form['keyType'])
            if requestedKeyType in validKeyTypes:
                if requestedKeyType == 2:
                    if current_user.has_role('Admin'):
                        validRequest = True
                else:
                    validRequest = True
        if validRequest is True:
            newapi = apikey.apikey(current_user.id, requestedKeyType, request.form['keyName'], request.form['expiration'])
            db.session.add(newapi)
            flash("New API Key Added", "success")
        else:
            flash("Invalid Key Type","error")
        db.session.commit()

    elif action == "delete":
        apiQuery = apikey.apikey.query.filter_by(key=request.form['key']).first()
        if apiQuery.userID == current_user.id:
            db.session.delete(apiQuery)
            db.session.commit()
            flash("API Key Deleted", "success")
        else:
            flash("Invalid API Key", "error")
    return redirect(url_for('.settings_apikeys_page'))


@settings_bp.route('/initialSetup', methods=['POST'])
def initialSetup():
    firstRunCheck = system.check_existing_settings()

    if firstRunCheck is False:
        cache.delete_memoized(cachedDbCalls.getSystemSettings)
        sysSettings = settings.settings.query.all()

        for setting in sysSettings:
            db.session.delete(setting)
        db.session.commit()

        username = request.form['username']
        emailAddress = request.form['email']
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

        # Whereas this code had worked before, it is now causing errors on post
        #validAddress = system.formatSiteAddress(serverAddress)
        #try:
        #    externalIP = socket.gethostbyname(validAddress)
        #except socket.gaierror:
        #    flash("Invalid Server Address/IP", "error")
        #    return redirect(url_for("settings.initialSetup"))

        if password1 == password2:

            passwordhash = hash_password(password1)

            user_datastore.create_user(email=emailAddress, username=username, password=passwordhash)
            db.session.commit()
            user = Sec.User.query.filter_by(username=username).first()
            user.uuid = str(uuid.uuid4())
            user.authType = 0
            user.confirmed_at = datetime.datetime.utcnow()
            user.xmppToken = str(os.urandom(32).hex())

            user_datastore.find_or_create_role(name='Admin', description='Administrator')
            user_datastore.find_or_create_role(name='User', description='User')
            user_datastore.find_or_create_role(name='Streamer', description='Streamer')
            user_datastore.find_or_create_role(name='Recorder', description='Recorder')
            user_datastore.find_or_create_role(name='Uploader', description='Uploader')

            user_datastore.add_role_to_user(user, 'Admin')
            user_datastore.add_role_to_user(user, 'Streamer')
            user_datastore.add_role_to_user(user, 'Recorder')
            user_datastore.add_role_to_user(user, 'Uploader')
            user_datastore.add_role_to_user(user, 'User')

            serverSettings = settings.settings(serverName, serverProtocol, serverAddress, smtpAddress, smtpPort,
                                               smtpTLS, smtpSSL, smtpUser, smtpPassword, smtpSendAs, recordSelect,
                                               uploadSelect, adaptiveStreaming, showEmptyTables, allowComments,
                                               globalvars.version)
            db.session.add(serverSettings)
            db.session.commit()

            sysSettings = cachedDbCalls.getSystemSettings()

            if settings is not None:
                current_app.config.update(
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
                    SECURITY_FORGOT_PASSWORD_TEMPLATE='security/forgot_password.html',
                    SECURITY_LOGIN_USER_TEMPLATE='security/login_user.html',
                    SECURITY_REGISTER_USER_TEMPLATE='security/register_user.html',
                    SECURITY_RESET_PASSWORD_TEMPLATE='security/reset_password.html',
                    SECURITY_SEND_CONFIRMATION_TEMPLATE='security/send_confirmation.html')

                email.init_app(current_app)
                email.app = current_app

                # Import Theme Data into Theme Dictionary
                with open('templates/themes/' + sysSettings.systemTheme + '/theme.json') as f:
                    globalvars.themeData = json.load(f)

        else:
            flash('Passwords do not match')
            return redirect(url_for('root.main_page'))

    return redirect(url_for('root.main_page'))
