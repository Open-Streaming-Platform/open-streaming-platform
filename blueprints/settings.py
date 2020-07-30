import os
import datetime
import json
import shutil
import uuid
import socket
import xmltodict
import git
import re

import requests
from flask import request, flash, render_template, redirect, url_for, Blueprint, current_app, Response, session, abort
from flask_security import current_user, login_required, roles_required
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

from functions import system
from functions import themes

from globals import globalvars

from app import user_datastore
from app import photos

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/user', methods=['POST', 'GET'])
@login_required
def user_page():
    if request.method == 'GET':
        return render_template(themes.checkOverride('userSettings.html'))
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
    channelSubList = subscriptions.channelSubs.query.filter_by(userID=current_user.id).all()

    return render_template(themes.checkOverride('subscriptions.html'), channelSubList=channelSubList)


@settings_bp.route('/user/addInviteCode')
@login_required
def user_addInviteCode():
    if 'inviteCode' in request.args:
        inviteCode = request.args.get("inviteCode")
        inviteCodeQuery = invites.inviteCode.query.filter_by(code=inviteCode).first()
        if inviteCodeQuery is not None:
            if inviteCodeQuery.isValid():
                existingInviteQuery = invites.invitedViewer.query.filter_by(inviteCode=inviteCodeQuery.id,
                                                                            userID=current_user.id).first()
                if existingInviteQuery is None:
                    if inviteCodeQuery.expiration is not None:
                        remainingDays = (inviteCodeQuery.expiration - datetime.datetime.now()).days
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
                system.newLog(3,
                              "User Attempted to add Expired Invite Code to Account - Username:" + current_user.username + " Channel ID #" + str(
                                  inviteCodeQuery.channelID))
                flash("Invite Code Expired", "error")
        else:
            flash("Invalid Invite Code", "error")
    return redirect(url_for('root.main_page'))


@settings_bp.route('/admin', methods=['POST', 'GET'])
@login_required
@roles_required('Admin')
def admin_page():
    videos_root = current_app.config['WEB_ROOT'] + 'videos/'
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

                    system.newLog(1, "User " + current_user.username + " deleted Topic " + str(topicQuery.name))
                    db.session.delete(topicQuery)
                    db.session.commit()

                    # Initialize the Topic Cache
                    topicQuery = topics.topics.query.all()
                    for topic in topicQuery:
                        globalvars.topicCache[topic.id] = topic.name

                    flash("Topic Deleted")
                    return redirect(url_for('.admin_page', page="topics"))

                elif setting == "users":
                    userID = int(request.args.get("userID"))

                    userQuery = Sec.User.query.filter_by(id=userID).first()

                    if userQuery is not None:

                        commentQuery = comments.videoComments.query.filter_by(userID=int(userID)).all()
                        for comment in commentQuery:
                            db.session.delete(comment)
                        db.session.commit()

                        inviteQuery = invites.invitedViewer.query.filter_by(userID=int(userID)).all()
                        for invite in inviteQuery:
                            db.session.delete(invite)
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

                            filePath = videos_root + chan.channelLoc

                            if filePath != videos_root:
                                shutil.rmtree(filePath, ignore_errors=True)

                            db.session.delete(chan)

                        flash("User " + str(userQuery.username) + " Deleted")
                        system.newLog(1, "User " + current_user.username + " deleted User " + str(userQuery.username))

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
            elif action == "backup":
                dbTables = db.engine.table_names()
                dbDump = {}
                for table in dbTables:
                    for c in db.Model._decl_class_registry.values():
                        if hasattr(c, '__table__') and c.__tablename__ == table:
                            tableDict = system.table2Dict(c)
                            dbDump[table] = tableDict
                userQuery = Sec.User.query.all()
                dbDump['roles'] = {}
                for user in userQuery:
                    userroles = user.roles
                    dbDump['roles'][user.username] = []
                    for role in userroles:
                        dbDump['roles'][user.username].append(role.name)
                dbDumpJson = json.dumps(dbDump)
                system.newLog(1, "User " + current_user.username + " Performed DB Backup Dump")
                return Response(dbDumpJson, mimetype='application/json', headers={
                    'Content-Disposition': 'attachment;filename=OSPBackup-' + str(datetime.datetime.now()) + '.json'})

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
        streamList = Stream.Stream.query.all()
        topicsList = topics.topics.query.all()
        edgeNodes = settings.edgeStreamer.query.all()

        defaultRoles = {}
        for role in roleList:
            defaultRoles[role.name] = role.default

        # 30 Days Viewer Stats
        viewersTotal = 0

        # Create List of 30 Day Viewer Stats
        statsViewsLiveDay = db.session.query(func.date(views.views.date), func.count(views.views.id)).filter(
            views.views.viewType == 0).filter(
            views.views.date > (datetime.datetime.now() - datetime.timedelta(days=30))).group_by(
            func.date(views.views.date)).all()
        statsViewsLiveDayArray = []
        for entry in statsViewsLiveDay:
            viewersTotal = viewersTotal + entry[1]
            statsViewsLiveDayArray.append({'t': (entry[0]), 'y': entry[1]})

        statsViewsRecordedDay = db.session.query(func.date(views.views.date), func.count(views.views.id)).filter(
            views.views.viewType == 1).filter(
            views.views.date > (datetime.datetime.now() - datetime.timedelta(days=30))).group_by(
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

        nginxStatDataRequest = requests.get('http://127.0.0.1:9000/stats')
        nginxStatData = (json.loads(json.dumps(xmltodict.parse(nginxStatDataRequest.text))))

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

        system.newLog(1, "User " + current_user.username + " Accessed Admin Interface")

        return render_template(themes.checkOverride('admin.html'), appDBVer=appDBVer, userList=userList,
                               roleList=roleList, channelList=channelList, streamList=streamList, topicsList=topicsList,
                               repoSHA=repoSHA, repoBranch=branch,
                               remoteSHA=remoteSHA, themeList=themeList, statsViewsDay=statsViewsDay,
                               viewersTotal=viewersTotal, currentViewers=currentViewers, nginxStatData=nginxStatData,
                               globalHooks=globalWebhookQuery, defaultRoleDict=defaultRoles,
                               logsList=logsList, edgeNodes=edgeNodes, oAuthProvidersList=oAuthProvidersList, ejabberdStatus=ejabberd, page=page)
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
            serverMessageTitle = request.form['serverMessageTitle']
            serverMessage = request.form['serverMessage']
            theme = request.form['theme']
            mainPageSort = request.form['mainPageSort']
            restreamMaxBitrate = request.form['restreamMaxBitrate']
            clipMaxLength = request.form['maxClipLength']

            recordSelect = False
            uploadSelect = False
            adaptiveStreaming = False
            showEmptyTables = False
            allowComments = False
            smtpTLS = False
            smtpSSL = False
            protectionEnabled = False
            maintenanceMode = False

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

            systemLogo = None
            if 'photo' in request.files:
                file = request.files['photo']
                if file.filename != '':
                    filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')
                    systemLogo = "/images/" + filename
                    themes.faviconGenerator(globalvars.videoRoot + 'images/' + filename)

            validAddress = system.formatSiteAddress(serverAddress)
            try:
                externalIP = socket.gethostbyname(validAddress)
            except socket.gaierror:
                flash("Invalid Server Address/IP", "error")
                return redirect(url_for(".admin_page", page="settings"))

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
            sysSettings.sortMainBy = int(mainPageSort)
            sysSettings.serverMessageTitle = serverMessageTitle
            sysSettings.serverMessage = serverMessage
            sysSettings.protectionEnabled = protectionEnabled
            sysSettings.restreamMaxBitrate = int(restreamMaxBitrate)
            sysSettings.maintenanceMode = maintenanceMode
            sysSettings.maxClipLength = int(clipMaxLength)

            if systemLogo is not None:
                sysSettings.systemLogo = systemLogo

            db.session.commit()

            sysSettings = settings.settings.query.first()

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

        elif settingType == "topics":

            if 'topicID' in request.form:
                topicID = int(request.form['topicID'])
                topicName = request.form['name']

                topicQuery = topics.topics.query.filter_by(id=topicID).first()

                if topicQuery is not None:

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

                topicImage = None
                if 'photo' in request.files:
                    file = request.files['photo']
                    if file.filename != '':
                        filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')
                        topicImage = filename

                newTopic = topics.topics(topicName, topicImage)
                db.session.add(newTopic)

            # Initialize the Topic Cache
            topicQuery = topics.topics.query.all()
            for topic in topicQuery:
                globalvars.topicCache[topic.id] = topic.name

            db.session.commit()
            return redirect(url_for('.admin_page', page="topics"))

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
                flash("Invalid OAuth Object","errror")
            return redirect(url_for('.admin_page', page="oauth"))

        elif settingType == "newuser":

            password = request.form['password1']
            emailAddress = request.form['emailaddress']
            username = request.form['username']

            passwordhash = hash_password(password)

            user_datastore.create_user(email=emailAddress, username=username, password=passwordhash)
            db.session.commit()

            user = Sec.User.query.filter_by(username=username).first()
            user_datastore.add_role_to_user(user, 'User')
            user.authType = 0
            user.confirmed_at = datetime.datetime.now()
            db.session.commit()
            return redirect(url_for('.admin_page', page="users"))

        return redirect(url_for('.admin_page'))

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


@settings_bp.route('/dbRestore', methods=['POST'])
def settings_dbRestore():
    validRestoreAttempt = False
    if not settings.settings.query.all():
        validRestoreAttempt = True
    elif current_user.is_authenticated:
        if current_user.has_role("Admin"):
            validRestoreAttempt = True

    if validRestoreAttempt:

        restoreJSON = None
        if 'restoreData' in request.files:
            file = request.files['restoreData']
            if file.filename != '':
                restoreJSON = file.read()
        if restoreJSON is not None:
            restoreDict = json.loads(restoreJSON)

            ## Restore Settings

            meta = db.metadata
            for table in reversed(meta.sorted_tables):
                db.session.execute(table.delete())
            db.session.commit()

            for roleData in restoreDict['role']:
                user_datastore.find_or_create_role(name=roleData['name'], description=roleData['description'])
            db.session.commit()

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
                                               eval(restoreDict['settings'][0]['allowComments']), globalvars.version)
            serverSettings.id = int(restoreDict['settings'][0]['id'])
            serverSettings.systemTheme = restoreDict['settings'][0]['systemTheme']
            serverSettings.systemLogo = restoreDict['settings'][0]['systemLogo']
            serverSettings.protectionEnabled = eval(restoreDict['settings'][0]['protectionEnabled'])
            if 'restreamMaxBitrate' in restoreDict['settings'][0]:
                serverSettings.restreamMaxBitrate = int(restoreDict['settings'][0]['restreamMaxBitrate'])
            if 'serverMessage' in restoreDict['settings'][0]:
                serverSettings.serverMessage = restoreDict['settings'][0]['serverMessage']
            if 'serverMessageTitle' in restoreDict['settings'][0]:
                serverSettings.serverMessageTitle = restoreDict['settings'][0]['serverMessageTitle']
            if 'mainPageSort' in restoreDict['settings'][0]:
                serverSettings.mainPageSort = int(restoreDict['settings'][0]['mainPageSort'])
            if 'maxClipLength' in restoreDict['settings'][0]:
                serverSettings.maxClipLength = int(restoreDict['settings'][0]['maxClipLength'])

            # Remove Old Settings
            oldSettings = settings.settings.query.all()
            for row in oldSettings:
                db.session.delete(row)
            db.session.commit()

            db.session.add(serverSettings)
            db.session.commit()

            sysSettings = settings.settings.query.first()

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

            ## Restore Edge Nodes
            oldEdgeNodes = settings.edgeStreamer.query.all()
            for node in oldEdgeNodes:
                db.session.delete(node)
            db.session.commit()

            if 'edgeStreamer' in restoreDict:
                for node in restoreDict['edgeStreamer']:
                    restoredNode = settings.edgeStreamer(node['address'], node['port'], node['loadPct'])
                    restoredNode.status = int(node['status'])
                    restoredNode.active = eval(node['active'])
                    db.session.add(restoredNode)
                    db.session.commit()

            ## Restores OAuth and Users
            oldUsers = Sec.User.query.all()
            for user in oldUsers:
                db.session.delete(user)
            db.session.commit()

            oldOAuth = settings.oAuthProvider.query.all()
            for provider in oldOAuth:
                db.session.delete(provider)
            db.session.commit()

            if 'o_auth_provider' in restoreDict:
                for provider in restoreDict['o_auth_provider']:
                    newOauthProvider = settings.oAuthProvider(provider['name'], provider['preset_auth_type'], provider['friendlyName'], provider['displayColor'],
                                                              provider['client_id'], provider['client_secret'], provider['access_token_url'], provider['authorize_url'],
                                                              provider['api_base_url'], provider['profile_endpoint'], provider['id_value'], provider['username_value'], provider['email_value'])
                    if provider['access_token_params'] != 'None':
                        newOauthProvider.access_token_params = provider['access_token_params']
                    if provider['authorize_params'] != 'None':
                        newOauthProvider.authorize_params = provider['authorize_params']
                    if provider['client_kwargs'] != 'None':
                        newOauthProvider.client_kwargs = provider['client_kwargs']
                    db.session.add(newOauthProvider)
                db.session.commit()

                providerQuery = settings.oAuthProvider.query.all()
                for provider in providerQuery:
                    oauth.register(
                        name=provider.name,
                        client_id=provider.client_id,
                        client_secret=provider.client_secret,
                        access_token_url=provider.access_token_url,
                        access_token_params=provider.access_token_params if provider.access_token_params != '' else None,
                        authorize_url=provider.authorize_url,
                        authorize_params=provider.authorize_params if provider.authorize_params != '' else None,
                        api_base_url=provider.api_base_url,
                        client_kwargs=json.loads(provider.client_kwargs) if provider.client_kwargs != '' else None,
                    )

            for restoredUser in restoreDict['user']:
                user_datastore.create_user(email=restoredUser['email'], username=restoredUser['username'],
                                           password=restoredUser['password'])
                db.session.commit()
                user = Sec.User.query.filter_by(username=restoredUser['username']).first()
                user.pictureLocation = restoredUser['pictureLocation']
                user.active = eval(restoredUser['active'])
                user.biography = restoredUser['biography']

                if 'uuid' in restoredUser:
                    user.uuid = str(restoredUser['uuid'])
                else:
                    user.uuid = str(uuid.uuid4())
                if 'authType' in restoredUser:
                    user.authType = int(restoredUser['authType'])
                else:
                    user.authType = 0
                if 'oAuthID' in restoredUser:
                    user.oAuthID = restoredUser['oAuthID']
                if 'oAuthProvider' in restoredUser:
                    user.oAuthProvider = restoredUser['oAuthProvider']
                if 'xmppToken' in restoredUser:
                    user.xmppToken = restoredUser['xmppToken']

                if restoredUser['confirmed_at'] != "None":
                    try:
                        user.confirmed_at = datetime.datetime.strptime(restoredUser['confirmed_at'],
                                                                       '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        user.confirmed_at = datetime.datetime.strptime(restoredUser['confirmed_at'],
                                                                       '%Y-%m-%d %H:%M:%S.%f')
                db.session.commit()

                user = Sec.User.query.filter_by(username=restoredUser['username']).first()
                user.id = int(restoredUser['id'])
                db.session.commit()

                user = Sec.User.query.filter_by(username=restoredUser['username']).first()
                for roleEntry in restoreDict['roles'][user.username]:
                    user_datastore.add_role_to_user(user, roleEntry)
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
                    channel.views = int(restoredChannel['views'])
                    channel.protected = eval(restoredChannel['protected'])
                    channel.channelMuted = eval(restoredChannel['channelMuted'])
                    channel.defaultStreamName = restoredChannel['defaultStreamName']
                    channel.showChatJoinLeaveNotification = eval(restoredChannel['showChatJoinLeaveNotification'])
                    channel.imageLocation = restoredChannel['imageLocation']
                    channel.offlineImageLocation = restoredChannel['offlineImageLocation']
                    channel.autoPublish = eval(restoredChannel['autoPublish'])
                    if 'rtmpRestream' in restoredChannel:
                        channel.rtmpRestream = eval(restoredChannel['rtmpRestream'])
                    if 'rtmpRestreamDestination' in restoredChannel:
                        channel.rtmpRestreamDestination = restoredChannel['rtmpRestreamDestination']
                    if 'xmppToken' in restoredChannel:
                        channel.xmppToken = restoredChannel['xmppToken']
                    else:
                        channel.xmppToken = str(os.urandom(32).hex())

                    db.session.add(channel)
                else:
                    flash("Error Restoring Channel: ID# " + str(restoredChannel['id']), "error")
            db.session.commit()

            ## Restore Subscriptions
            oldSubscriptions = subscriptions.channelSubs.query.all()
            for sub in oldSubscriptions:
                db.session.delete(sub)
            db.session.commit()

            if 'channel_subs' in restoreDict:
                for restoredChannelSub in restoreDict['channel_subs']:
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
                                                                int(restoredVideo['channelID']),
                                                                restoredVideo['channelName'],
                                                                int(restoredVideo['topic']),
                                                                int(restoredVideo['views']),
                                                                restoredVideo['videoLocation'],
                                                                datetime.datetime.strptime(restoredVideo['videoDate'],
                                                                                           '%Y-%m-%d %H:%M:%S'),
                                                                eval(restoredVideo['allowComments']),
                                                                eval(restoredVideo['published']))
                        except ValueError:
                            video = RecordedVideo.RecordedVideo(int(restoredVideo['owningUser']),
                                                                int(restoredVideo['channelID']),
                                                                restoredVideo['channelName'],
                                                                int(restoredVideo['topic']),
                                                                int(restoredVideo['views']),
                                                                restoredVideo['videoLocation'],
                                                                datetime.datetime.strptime(restoredVideo['videoDate'],
                                                                                           '%Y-%m-%d %H:%M:%S.%f'),
                                                                eval(restoredVideo['allowComments']),
                                                                eval(restoredVideo['published']))
                        video.id = int(restoredVideo['id'])
                        video.description = restoredVideo['description']
                        if restoredVideo['length'] != "None":
                            video.length = float(restoredVideo['length'])
                        video.thumbnailLocation = restoredVideo['thumbnailLocation']
                        video.pending = eval(restoredVideo['pending'])
                        video.published = eval(restoredVideo['published'])
                        if 'gifLocation' in restoredVideo:
                            if restoredVideo['gifLocation'] != "None":
                                video.gifLocation = restoredVideo['gifLocation']
                        if 'uuid' in restoredVideo:
                            video.uuid = str(restoredVideo['uuid'])
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
                        videoLocation = None
                        if 'videoLocation' not in restoredClip:
                            videoLocation = restoredClip['videoLocation']
                        newClip = RecordedVideo.Clips(int(restoredClip['parentVideo']), videoLocation, float(restoredClip['startTime']), float(restoredClip['endTime']), restoredClip['clipName'], restoredClip['description'])
                        newClip.id = int(restoredClip['id'])
                        newClip.views = int(restoredClip['views'])
                        newClip.thumbnailLocation = restoredClip['thumbnailLocation']
                        newClip.published = eval(restoredClip['published'])
                        if 'uuid' in restoredClip:
                            newClip.uuid = str(restoredClip['uuid'])
                        if 'gifLocation' in restoredClip:
                            if restoredClip['gifLocation'] != "None":
                                newClip.gifLocation = restoredClip['gifLocation']
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
                    if restoredAPIKey['expiration'] != "None":
                        try:
                            key.createdOn = datetime.datetime.strptime(restoredAPIKey['createdOn'], '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            key.createdOn = datetime.datetime.strptime(restoredAPIKey['createdOn'],
                                                                       '%Y-%m-%d %H:%M:%S.%f')
                        try:
                            key.expiration = datetime.datetime.strptime(restoredAPIKey['expiration'],
                                                                        '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            key.expiration = datetime.datetime.strptime(restoredAPIKey['expiration'],
                                                                        '%Y-%m-%d %H:%M:%S.%f')
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
                                             int(restoredWebhook['requestType']),
                                             int(restoredWebhook['requestTrigger']))
                db.session.add(hook)
            db.session.commit()

            ## Restores Views
            oldViews = views.views.query.all()
            for view in oldViews:
                db.session.delete(view)
            db.session.commit()

            if 'restoreVideos' in request.form:
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
                    if restoredInvitedViewer['expiration'] is not None:
                        try:
                            invite.expiration = datetime.datetime.strptime(restoredInvitedViewer['expiration'],
                                                                           '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            invite.expiration = datetime.datetime.strptime(restoredInvitedViewer['expiration'],
                                                                           '%Y-%m-%d %H:%M:%S.%f')
                    if 'inviteCode' in restoredInvitedViewer:
                        if restoredInvitedViewer['inviteCode'] is not None:
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
                            comment.timestamp = datetime.datetime.strptime(restoredComment['timestamp'],
                                                                           '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            comment.timestamp = datetime.datetime.strptime(restoredComment['timestamp'],
                                                                           '%Y-%m-%d %H:%M:%S.%f')
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

            if 'restoreVideos' in request.form:
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
            if 'restoreVideos' in request.form:
                for restoredUpvote in restoreDict['comment_upvotes']:
                    if restoredUpvote['userID'] != "None" and restoredUpvote['commentID'] != "None":
                        upvote = upvotes.commentUpvotes(int(restoredUpvote['userID']), int(restoredUpvote['commentID']))
                        upvote.id = int(restoredUpvote['id'])
                        db.session.add(upvote)
                    else:
                        flash("Error Restoring Upvote: ID# " + str(restoredUpvote['id']), "error")

            # Logic to Check the DB Version
            dbVersionQuery = dbVersion.dbVersion.query.first()

            if dbVersionQuery is None:
                newDBVersion = dbVersion.dbVersion(globalvars.appDBVersion)
                db.session.add(newDBVersion)
                db.session.commit()

            db.session.commit()

            # Import Theme Data into Theme Dictionary
            with open('templates/themes/' + sysSettings.systemTheme + '/theme.json') as f:

                globalvars.themeData = json.load(f)

            flash("Database Restored from Backup", "success")
            session.clear()
            return redirect(url_for('root.main_page', page="backup"))

    else:
        if settings.settings.query.all():
            flash("Invalid Restore Attempt", "error")
            return redirect(url_for('root.main_page'))
        else:
            return redirect(url_for('.initialSetup'))


@settings_bp.route('/channels', methods=['POST', 'GET'])
@login_required
@roles_required('Streamer')
def settings_channels_page():
    sysSettings = settings.settings.query.first()

    videos_root = current_app.config['WEB_ROOT'] + 'videos/'

    if request.method == 'POST':

        requestType = request.form['type']
        channelName = system.strip_html(request.form['channelName'])
        topic = request.form['channeltopic']
        description = system.strip_html(request.form['description'])

        record = False

        if 'recordSelect' in request.form and sysSettings.allowRecording is True:
            record = True

        autoPublish = False
        if 'publishSelect' in request.form:
            autoPublish = True

        rtmpRestream = False
        if 'rtmpSelect' in request.form:
            rtmpRestream = True

        chatEnabled = False

        if 'chatSelect' in request.form:
            chatEnabled = True

        allowComments = False

        if 'allowComments' in request.form:
            allowComments = True

        protection = False

        if 'channelProtection' in request.form:
            protection = True

        if requestType == 'new':

            newUUID = str(uuid.uuid4())

            newChannel = Channel.Channel(current_user.id, newUUID, channelName, topic, record, chatEnabled,
                                         allowComments, description)

            if 'photo' in request.files:
                file = request.files['photo']
                if file.filename != '':
                    filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')
                    newChannel.imageLocation = filename

            # Establish XMPP Channel
            from app import ejabberd
            ejabberd.create_room(newChannel.channelLoc, 'conference.' + sysSettings.siteAddress, sysSettings.siteAddress)
            ejabberd.set_room_affiliation(newChannel.channelLoc, 'conference.' + sysSettings.siteAddress, (current_user.username) + "@" + sysSettings.siteAddress, "owner")

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

            rtmpRestreamDestination = request.form['rtmpDestination']

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
                requestedChannel.protected = protection
                requestedChannel.defaultStreamName = defaultstreamName
                requestedChannel.autoPublish = autoPublish
                requestedChannel.rtmpRestream = rtmpRestream
                requestedChannel.rtmpRestreamDestination = rtmpRestreamDestination

                vanityURL = None
                if 'vanityURL' in request.form:
                    requestedVanityURL = request.form['vanityURL']
                    requestedVanityURL = re.sub('[^A-Za-z0-9]+', '', requestedVanityURL)
                    if requestedVanityURL != '':
                        existingChannnelQuery = Channel.Channel.query.filter_by(vanityURL=requestedVanityURL).first()
                        if existingChannnelQuery is None:
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

                flash("Channel Edited")
                db.session.commit()
            else:
                flash("Invalid Change Attempt", "Error")
            redirect(url_for('.settings_channels_page'))

    topicList = topics.topics.query.all()
    user_channels = Channel.Channel.query.filter_by(owningUser=current_user.id).all()

    # Get xmpp room options
    from app import ejabberd
    channelRooms = {}
    channelMods = {}
    for chan in user_channels:
        xmppQuery = ejabberd.get_room_options(chan.channelLoc, 'conference.' + sysSettings.siteAddress)
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

    return render_template(themes.checkOverride('user_channels.html'), channels=user_channels, topics=topicList, channelRooms=channelRooms, channelMods=channelMods,
                           viewStats=user_channels_stats)


@settings_bp.route('/channels/chat', methods=['POST', 'GET'])
@login_required
@roles_required('Streamer')
def settings_channels_chat_page():
    sysSettings = settings.settings.query.first()

    if request.method == 'POST':
        from app import ejabberd
        channelLoc = system.strip_html(request.form['channelLoc'])
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
        newapi = apikey.apikey(current_user.id, 1, request.form['keyName'], request.form['expiration'])
        db.session.add(newapi)
        db.session.commit()
        flash("New API Key Added", "success")
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

        validAddress = system.formatSiteAddress(serverAddress)
        try:
            externalIP = socket.gethostbyname(validAddress)
        except socket.gaierror:
            flash("Invalid Server Address/IP", "error")
            return redirect(url_for("initialSetup"))

        if password1 == password2:

            passwordhash = hash_password(password1)

            user_datastore.create_user(email=emailAddress, username=username, password=passwordhash)
            db.session.commit()
            user = Sec.User.query.filter_by(username=username).first()
            user.uuid = str(uuid.uuid4())
            user.authType = 0
            user.confirmed_at = datetime.datetime.now()
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

            sysSettings = settings.settings.query.first()

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