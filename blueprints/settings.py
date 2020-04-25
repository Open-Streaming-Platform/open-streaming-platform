import os
import datetime
import json
import shutil
import uuid
import socket
import xmltodict
import git

import requests
from flask import request, flash, render_template, redirect, url_for, Blueprint, current_app, Response, session, abort
from flask_security import current_user, login_required, roles_required
from flask_security.utils import hash_password
from sqlalchemy.sql.expression import func

from werkzeug.utils import secure_filename

from classes.shared import db, email
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
        emailAddress = request.form['emailAddress']
        password1 = request.form['password1']
        password2 = request.form['password2']
        biography = request.form['biography']

        if password1 != "":
            if password1 == password2:
                newPassword = hash_password(password1)
                current_user.password = newPassword
                system.newLog(1, "User Password Changed - Username:" + current_user.username)
                flash("Password Changed")
            else:
                flash("Passwords Don't Match!")

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

        current_user.email = emailAddress

        current_user.biography = biography
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
@roles_required('Streamer')
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
    return redirect(url_for('main_page'))


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
                    flash("Topic Deleted")
                    return redirect(url_for('.admin_page', page="topics"))

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

                    filePath = videos_root + channelQuery.channelLoc

                    if filePath != videos_root:
                        shutil.rmtree(filePath, ignore_errors=True)

                    system.newLog(1, "User " + current_user.username + " deleted Channel " + str(channelQuery.id))
                    db.session.delete(channelQuery)
                    db.session.commit()

                    flash("Channel Deleted")
                    return redirect(url_for('.admin_page', page="channels"))

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

        system.newLog(1, "User " + current_user.username + " Accessed Admin Interface")

        return render_template(themes.checkOverride('admin.html'), appDBVer=appDBVer, userList=userList,
                               roleList=roleList, channelList=channelList, streamList=streamList, topicsList=topicsList,
                               repoSHA=repoSHA, repoBranch=branch,
                               remoteSHA=remoteSHA, themeList=themeList, statsViewsDay=statsViewsDay,
                               viewersTotal=viewersTotal, currentViewers=currentViewers, nginxStatData=nginxStatData,
                               globalHooks=globalWebhookQuery,
                               logsList=logsList, edgeNodes=edgeNodes, page=page)
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
            restreamMaxBitrate = request.form['restreamMaxBitrate']

            recordSelect = False
            uploadSelect = False
            adaptiveStreaming = False
            showEmptyTables = False
            allowComments = False
            smtpTLS = False
            smtpSSL = False
            protectionEnabled = False

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

            systemLogo = None
            if 'photo' in request.files:
                file = request.files['photo']
                if file.filename != '':
                    filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')
                    systemLogo = "/images/" + filename

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
            sysSettings.serverMessageTitle = serverMessageTitle
            sysSettings.serverMessage = serverMessage
            sysSettings.protectionEnabled = protectionEnabled
            sysSettings.restreamMaxBitrate = int(restreamMaxBitrate)

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
                SECURITY_FORGOT_PASSWORD_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/forgot_password.html',
                SECURITY_LOGIN_USER_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/login_user.html',
                SECURITY_REGISTER_USER_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/register_user.html',
                SECURITY_RESET_PASSWORD_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/reset_password.html',
                SECURITY_SEND_CONFIRMATION_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/send_confirmation.html')

            email.init_app(current_app)
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

        elif settingType == "newuser":

            password = request.form['password1']
            emailAddress = request.form['emailaddress']
            username = request.form['username']

            passwordhash = hash_password(password)

            user_datastore.create_user(email=emailAddress, username=username, password=passwordhash)
            db.session.commit()

            user = Sec.User.query.filter_by(username=username).first()
            user_datastore.add_role_to_user(user, 'User')
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
        return (data)
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
                serverSettings.restreamMaxBitrate = restoreDict['settings'][0]['restreamMaxBitrate']
            if 'serverMessage' in restoreDict['settings'][0]:
                serverSettings.serverMessage = restoreDict['settings'][0]['serverMessage']
            if 'serverMessageTitle' in restoreDict['settings'][0]:
                serverSettings.serverMessageTitle = restoreDict['settings'][0]['serverMessageTitle']

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
                    SECURITY_FORGOT_PASSWORD_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/forgot_password.html',
                    SECURITY_LOGIN_USER_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/login_user.html',
                    SECURITY_REGISTER_USER_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/register_user.html',
                    SECURITY_RESET_PASSWORD_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/reset_password.html',
                    SECURITY_SEND_CONFIRMATION_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/send_confirmation.html')

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
                user.pictureLocation = restoredUser['pictureLocation']
                user.active = eval(restoredUser['active'])
                user.biography = restoredUser['biography']

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
                    channel.autoPublish = eval(restoredChannel['autoPublish'])
                    if 'rtmpRestream' in restoredChannel:
                        channel.rtmpRestream = eval(restoredChannel['rtmpRestream'])
                    if 'rtmpRestreamDestination' in restoredChannel:
                        channel.rtmpRestreamDestination = restoredChannel['rtmpRestreamDestination']

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
                        newClip = RecordedVideo.Clips(int(restoredClip['parentVideo']),
                                                      float(restoredClip['startTime']),
                                                      float(restoredClip['endTime']), restoredClip['clipName'],
                                                      restoredClip['description'])
                        newClip.id = int(restoredClip['id'])
                        newClip.views = int(restoredClip['views'])
                        newClip.thumbnailLocation = restoredClip['thumbnailLocation']
                        newClip.published = eval(restoredClip['published'])
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
            return redirect(url_for('main_page', page="backup"))

    else:
        if settings.settings.query.all():
            flash("Invalid Restore Attempt", "error")
            return redirect(url_for('main_page'))
        else:
            return redirect(url_for('.initialSetup'))


@settings_bp.route('/channels', methods=['POST', 'GET'])
@login_required
@roles_required('Streamer')
def settings_channels_page():
    sysSettings = settings.settings.query.first()
    channelChatBGOptions = [{'name': 'Default', 'value': 'Standard'}, {'name': 'Plain White', 'value': 'PlainWhite'},
                            {'name': 'Deep Space', 'value': 'DeepSpace'}, {'name': 'Blood Red', 'value': 'BloodRed'},
                            {'name': 'Terminal', 'value': 'Terminal'}, {'name': 'Lawrencium', 'value': 'Lawrencium'},
                            {'name': 'Lush', 'value': 'Lush'}, {'name': 'Transparent', 'value': 'Transparent'}]
    channelChatAnimationOptions = [{'name': 'No Animation', 'value': 'None'},
                                   {'name': 'Slide-in From Left', 'value': 'slide-in-left'},
                                   {'name': 'Slide-In Blurred From Left', 'value': 'slide-in-blurred-left'},
                                   {'name': 'Fade-In', 'value': 'fade-in-fwd'}]
    videos_root = current_app.config['WEB_ROOT'] + 'videos/'

    if request.method == 'GET':
        if request.args.get("action") is not None:
            action = request.args.get("action")
            streamKey = request.args.get("streamkey")

            requestedChannel = Channel.Channel.query.filter_by(streamKey=streamKey).first()

            if action == "delete":
                if current_user.id == requestedChannel.owningUser:

                    filePath = videos_root + requestedChannel.channelLoc
                    if filePath != videos_root:
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
                    flash("Invalid Deletion Attempt", "Error")

    elif request.method == 'POST':

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

        chatJoinNotifications = False
        if 'chatJoinNotificationSelect' in request.form:
            chatJoinNotifications = True

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

            db.session.add(newChannel)
            db.session.commit()

        elif requestType == 'change':
            streamKey = request.form['streamKey']
            origStreamKey = request.form['origStreamKey']

            chatBG = request.form['chatBG']
            chatAnimation = request.form['chatAnimation']
            chatTextColor = request.form['chatTextColor']

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
                requestedChannel.chatBG = chatBG
                requestedChannel.showChatJoinLeaveNotification = chatJoinNotifications
                requestedChannel.chatAnimation = chatAnimation
                requestedChannel.chatTextColor = chatTextColor
                requestedChannel.protected = protection
                requestedChannel.defaultStreamName = defaultstreamName
                requestedChannel.autoPublish = autoPublish
                requestedChannel.rtmpRestream = rtmpRestream
                requestedChannel.rtmpRestreamDestination = rtmpRestreamDestination

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

    return render_template(themes.checkOverride('user_channels.html'), channels=user_channels, topics=topicList,
                           viewStats=user_channels_stats, channelChatBGOptions=channelChatBGOptions,
                           channelChatAnimationOptions=channelChatAnimationOptions)


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

        validAddress = system.formatSiteAddress(serverAddress)
        try:
            externalIP = socket.gethostbyname(validAddress)
        except socket.gaierror:
            flash("Invalid Server Address/IP", "error")
            return redirect(url_for("initialSetup"))

        if password1 == password2:

            passwordhash = hash_password(password1)

            user_datastore.create_user(email=email, username=username, password=passwordhash)
            db.session.commit()
            user = Sec.User.query.filter_by(username=username).first()
            user.confirmed_at = datetime.datetime.now()

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
                    SECURITY_FORGOT_PASSWORD_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/forgot_password.html',
                    SECURITY_LOGIN_USER_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/login_user.html',
                    SECURITY_REGISTER_USER_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/register_user.html',
                    SECURITY_RESET_PASSWORD_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/reset_password.html',
                    SECURITY_SEND_CONFIRMATION_TEMPLATE='themes/' + sysSettings.systemTheme + '/security/send_confirmation.html')

                email.init_app(current_app)
                email.app = current_app

                # Import Theme Data into Theme Dictionary
                with open('templates/themes/' + sysSettings.systemTheme + '/theme.json') as f:
                    globalvars.themeData = json.load(f)

        else:
            flash('Passwords do not match')
            return redirect(url_for('main_page'))

    return redirect(url_for('main_page'))