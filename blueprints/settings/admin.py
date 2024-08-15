import os
import datetime
import json
import uuid
import xmltodict
import pytz

import requests
from flask import (
    request,
    flash,
    render_template,
    redirect,
    url_for,
    Blueprint,
    session,
    abort,
)
from flask_security import (
    current_user,
    login_required,
    roles_required,
)
from flask_security.utils import hash_password
from sqlalchemy.sql.expression import func

from classes.shared import db, email, oauth
from classes import Stream
from classes import Channel
from classes import dbVersion
from classes import RecordedVideo
from classes import topics
from classes import settings
from classes import banList
from classes import Sec
from classes import views
from classes import webhook
from classes import logs
from classes import stickers
from classes import panel
from classes import hub
from classes.shared import cache

from functions import system
from functions import themes
from functions import cachedDbCalls
from functions import securityFunc
from functions.scheduled_tasks import video_tasks, channel_tasks

from globals import globalvars

from app import user_datastore
from app import photos
from app import stickerUploads


admin_settings_bp = Blueprint("admin_settings", __name__, url_prefix="/admin")


@admin_settings_bp.route("/", methods=["POST", "GET"])
@login_required
@roles_required("Admin")
def admin_page():
    if request.method == "GET":
        page = None

        appDBVer = dbVersion.dbVersion.query.first().version
        userList = Sec.User.query.all()
        roleList = Sec.Role.query.all()
        channelList = Channel.Channel.query.with_entities(
            Channel.Channel.id,
            Channel.Channel.channelName,
            Channel.Channel.imageLocation,
            Channel.Channel.owningUser,
            Channel.Channel.topic,
            Channel.Channel.channelLoc,
            Channel.Channel.views,
            Channel.Channel.chatEnabled,
            Channel.Channel.record,
            Channel.Channel.allowComments,
            Channel.Channel.protected,
            Channel.Channel.private,
            Channel.Channel.allowGuestNickChange,
        )
        streamList = (
            Stream.Stream.query.filter_by(active=True)
            .with_entities(
                Stream.Stream.id,
                Stream.Stream.linkedChannel,
                Stream.Stream.streamName,
                Stream.Stream.topic,
                Stream.Stream.currentViewers,
                Stream.Stream.startTimestamp,
                Stream.Stream.endTimeStamp,
                Stream.Stream.totalViewers,
            )
            .all()
        )
        streamHistory = (
            Stream.Stream.query.filter_by(active=False)
            .with_entities(
                Stream.Stream.id,
                Stream.Stream.startTimestamp,
                Stream.Stream.endTimeStamp,
                Stream.Stream.linkedChannel,
                Stream.Stream.streamName,
                Stream.Stream.totalViewers,
            )
            .order_by(Stream.Stream.startTimestamp.desc())
            .limit(100)
        )
        topicsList = cachedDbCalls.getAllTopics()
        rtmpServers = settings.rtmpServer.query.all()
        edgeNodes = settings.edgeStreamer.query.all()

        defaultRoles = {}
        for role in roleList:
            defaultRoles[role.name] = role.default

        # 30 Days Viewer Stats
        viewersTotal = 0

        # Create List of 30 Day Viewer Stats
        statsViewsLiveDay = (
            db.session.query(func.date(views.views.date), func.count(views.views.id))
            .filter(views.views.viewType == 0)
            .filter(
                views.views.date
                > (datetime.datetime.utcnow() - datetime.timedelta(days=30))
            )
            .group_by(func.date(views.views.date))
            .all()
        )
        statsViewsLiveDayArray = []
        for entry in statsViewsLiveDay:
            viewersTotal = viewersTotal + entry[1]
            statsViewsLiveDayArray.append({"t": (entry[0]), "y": entry[1]})

        statsViewsRecordedDay = (
            db.session.query(func.date(views.views.date), func.count(views.views.id))
            .filter(views.views.viewType == 1)
            .filter(
                views.views.date
                > (datetime.datetime.utcnow() - datetime.timedelta(days=30))
            )
            .group_by(func.date(views.views.date))
            .all()
        )
        statsViewsRecordedDayArray = []

        for entry in statsViewsRecordedDay:
            viewersTotal = viewersTotal + entry[1]
            statsViewsRecordedDayArray.append({"t": (entry[0]), "y": entry[1]})

        statsViewsDay = {
            "live": statsViewsLiveDayArray,
            "recorded": statsViewsRecordedDayArray,
        }

        currentViewers = 0
        for stream in streamList:
            currentViewers = currentViewers + stream.currentViewers

        try:
            nginxStatDataRequest = requests.get("http://127.0.0.1:9000/stats")
            nginxStatData = json.loads(
                json.dumps(xmltodict.parse(nginxStatDataRequest.text))
            )
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
            flash(
                "EJabberD is not connected and is required to access this page.  Contact your administrator",
                "error",
            )
            return redirect(url_for("root.main_page"))

        # Generate CSV String for Banned Chat List
        bannedWordQuery = banList.chatBannedWords.query.all()
        bannedWordArray = []
        for bannedWord in bannedWordQuery:
            bannedWordArray.append(bannedWord.word)
        bannedWordArray = sorted(bannedWordArray)
        bannedWordString = ",".join(bannedWordArray)

        globalPanelList = panel.globalPanel.query.all()
        mainPagePanelMapping = panel.panelMapping.query.filter_by(
            pageName="root.main_page", panelType=0
        )
        mainPagePanelMappingSort = sorted(
            mainPagePanelMapping, key=lambda x: x.panelOrder
        )

        globalStickers = stickers.stickers.query.filter_by(channelID=None).all()

        system.newLog(1, "User " + current_user.username + " Accessed Admin Interface")

        from classes.shared import celery

        nodes = celery.control.inspect(["celery@osp"])
        scheduled = nodes.scheduled()
        active = nodes.active()
        claimed = nodes.reserved()
        schedulerList = {
            "nodes": nodes,
            "scheduled": scheduled,
            "active": active,
            "claimed": claimed,
        }

        ospHub = hub.hub.query.first() 

        return render_template(
            themes.checkOverride("admin.html"),
            appDBVer=appDBVer,
            userList=userList,
            roleList=roleList,
            channelList=channelList,
            streamList=streamList,
            streamHistory=streamHistory,
            topicsList=topicsList,
            themeList=themeList,
            statsViewsDay=statsViewsDay,
            viewersTotal=viewersTotal,
            currentViewers=currentViewers,
            nginxStatData=nginxStatData,
            globalHooks=globalWebhookQuery,
            defaultRoleDict=defaultRoles,
            logsList=logsList,
            edgeNodes=edgeNodes,
            rtmpServers=rtmpServers,
            oAuthProvidersList=oAuthProvidersList,
            ejabberdStatus=ejabberd,
            bannedWords=bannedWordString,
            globalStickers=globalStickers,
            page=page,
            timeZoneOptions=pytz.all_timezones,
            schedulerList=schedulerList,
            globalPanelList=globalPanelList,
            mainPagePanelMapping=mainPagePanelMappingSort,
            ospHub=ospHub
        )
    elif request.method == "POST":

        settingType = request.form["settingType"]

        if settingType == "system":

            sysSettings = settings.settings.query.first()

            serverName = request.form["serverName"]
            serverProtocol = request.form["siteProtocol"]
            serverAddress = request.form["serverAddress"]
            serverMessageTitle = request.form["serverMessageTitle"]
            serverMessage = request.form["serverMessage"]
            theme = request.form["theme"]

            restreamMaxBitrate = request.form["restreamMaxBitrate"]
            clipMaxLength = request.form["maxClipLength"]

            recordSelect = False
            uploadSelect = False
            adaptiveStreaming = False
            showEmptyTables = False
            allowComments = False
            buildEdgeOnRestart = False
            protectionEnabled = False
            maintenanceMode = False
            webRTCPlaybackEnabled = False

            # OSP Proxy Settings
            if "ospProxyFQDN" in request.form:
                ospProxyFQDNForm = request.form["ospProxyFQDN"]
                ospProxyFQDNForm = ospProxyFQDNForm.lower()
                ospProxyFQDNForm = ospProxyFQDNForm.replace("http://", "")
                ospProxyFQDNForm = ospProxyFQDNForm.replace("https://", "")
                if ospProxyFQDNForm.strip() == "":
                    ospProxyFQDN = None
                else:
                    ospProxyFQDN = ospProxyFQDNForm
                sysSettings.proxyFQDN = ospProxyFQDN

            if "buildEdgeOnRestartSelect" in request.form:
                buildEdgeOnRestart = True

            if "recordSelect" in request.form:
                recordSelect = True

            if "uploadSelect" in request.form:
                uploadSelect = True

            if "adaptiveStreaming" in request.form:
                adaptiveStreaming = True

            if "showEmptyTables" in request.form:
                showEmptyTables = True

            if "allowComments" in request.form:
                allowComments = True

            if "enableProtection" in request.form:
                protectionEnabled = True
            if "maintenanceMode" in request.form:
                maintenanceMode = True
            if "enableWebRTC" in request.form:
                webRTCPlaybackEnabled = True

            if "bannedChatWords" in request.form:
                bannedWordListString = request.form["bannedChatWords"]
                bannedWordList = bannedWordListString.split(",")
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

            systemLogo = None
            if "photo" in request.files:
                file = request.files["photo"]
                if file.filename != "":
                    filename = photos.save(
                        request.files["photo"], name=str(uuid.uuid4()) + "."
                    )
                    systemLogo = "/images/" + filename
                    themes.faviconGenerator(globalvars.videoRoot + "images/" + filename)

            sysSettings.siteName = serverName
            sysSettings.siteProtocol = serverProtocol
            sysSettings.siteAddress = serverAddress
            sysSettings.allowRecording = recordSelect
            sysSettings.allowUploads = uploadSelect
            sysSettings.adaptiveStreaming = adaptiveStreaming
            sysSettings.showEmptyTables = showEmptyTables
            sysSettings.allowComments = allowComments
            sysSettings.systemTheme = theme
            sysSettings.webrtcPlaybackEnabled = webRTCPlaybackEnabled
            if "mainPageSort" in request.form:
                sysSettings.sortMainBy = int(request.form["mainPageSort"])
            if "limitMaxChannels" in request.form:
                sysSettings.limitMaxChannels = int(request.form["limitMaxChannels"])
            if "maxVideoRetention" in request.form:
                sysSettings.maxVideoRetention = max(0, int(request.form["maxVideoRetention"]))
            if "maxClipRetention" in request.form:
                sysSettings.maxClipRetention = max(0, int(request.form["maxClipRetention"]))
            if "maxVideoUploadFileSize" in request.form:
                sysSettings.maxVideoUploadFileSize = int(request.form["maxVideoUploadFileSize"])
            if "maxThumbnailUploadFileSize" in request.form:
                sysSettings.maxThumbnailUploadFileSize = int(request.form["maxThumbnailUploadFileSize"])
            if "maxStickerUploadFileSize" in request.form:
                sysSettings.maxStickerUploadFileSize = int(request.form['maxStickerUploadFileSize'])
            # Check enableRTMPRestream - Workaround to pre 0.9.x themes, by checking for the existance of 'mainPageSort' which does not exist in >= 0.9.x
            if "enableRTMPRestream" in request.form:
                sysSettings.allowRestream = True
            elif "mainPageSort" not in request.form:
                sysSettings.allowRestream = False
            if "serverTimeZone" in request.form:
                sysSettings.serverTimeZone = request.form["serverTimeZone"]
            else:
                sysSettings.serverTimeZone = "UTC"
            sysSettings.serverMessageTitle = serverMessageTitle
            sysSettings.serverMessage = serverMessage
            sysSettings.protectionEnabled = protectionEnabled
            sysSettings.restreamMaxBitrate = int(restreamMaxBitrate)
            sysSettings.maintenanceMode = maintenanceMode
            sysSettings.maxClipLength = int(clipMaxLength)
            sysSettings.buildEdgeOnRestart = buildEdgeOnRestart
            sysSettings.webrtcSignalProtocol = request.form[
                "webRTCSignalEndpointProtocol"
            ]
            if request.form["webRTCSignalEndpoint"].strip() != "":
                sysSettings.webrtcSignalURL = request.form[
                    "webRTCSignalEndpoint"
                ].strip()
            else:
                sysSettings.webrtcSignalURL = None

            if systemLogo is not None:
                sysSettings.systemLogo = systemLogo

            db.session.commit()

            cache.delete_memoized(cachedDbCalls.getSystemSettings)
            sysSettings = cachedDbCalls.getSystemSettings()

            themeList = []
            themeDirectorySearch = os.listdir("./templates/themes/")
            for theme in themeDirectorySearch:
                hasJSON = os.path.isfile("./templates/themes/" + theme + "/theme.json")
                if hasJSON:
                    themeList.append(theme)

            # Import Theme Data into Theme Dictionary
            with open(
                "templates/themes/" + sysSettings.systemTheme + "/theme.json"
            ) as f:

                globalvars.themeData = json.load(f)

            system.newLog(
                1, "User " + current_user.username + " altered System Settings"
            )

            return redirect(url_for(".admin_page", page="settings"))

        elif settingType == "newSticker":
            if "stickerName" in request.form:
                sysSettings = cachedDbCalls.getSystemSettings()
                
                stickerName = request.form["stickerName"]
                existingStickerNameQuery = stickers.stickers.query.filter_by(
                    name=stickerName
                ).with_entities(stickers.stickers.id).first()
                if existingStickerNameQuery is None:
                    if "stickerUpload" in request.files:
                        file = request.files["stickerUpload"]
                        if file.filename != "":
                            file.seek(0, os.SEEK_END)
                            fileSizeMiB = file.tell() / 1048576
                            file.seek(0, os.SEEK_SET)

                            if fileSizeMiB > sysSettings.maxStickerUploadFileSize:
                                flash(f"{file.filename} is too big.", "error")
                                return redirect(url_for(".admin_page", page="stickers"))

                            fileName = stickerUploads.save(
                                request.files["stickerUpload"],
                                name=stickerName + ".",
                                folder="stickers",
                            )
                            fileName = fileName.replace("stickers/", "")
                            newSticker = stickers.stickers(stickerName, fileName)
                            db.session.add(newSticker)
                            db.session.commit()
                else:
                    flash("Sticker Name Already Exists", "error")
            else:
                flash("Sticker Name Missing", "error")
            return redirect(url_for(".admin_page", page="stickers"))

        elif settingType == "topics":

            if "topicID" in request.form and request.form["topicID"] != "None":
                topicID = int(request.form["topicID"])
                topicName = request.form["name"]

                topicQuery = topics.topics.query.filter_by(id=topicID).first()

                if topicQuery is not None:
                    cache.delete_memoized(cachedDbCalls.getAllTopics)

                    topicQuery.name = topicName

                    if "photo" in request.files:
                        file = request.files["photo"]
                        if file.filename != "":
                            oldImage = None

                            if topicQuery.iconClass is not None:
                                oldImage = topicQuery.iconClass

                            filename = photos.save(
                                request.files["photo"], name=str(uuid.uuid4()) + "."
                            )
                            topicQuery.iconClass = filename

                            if oldImage is not None:
                                try:
                                    os.remove(oldImage)
                                except OSError:
                                    pass
            else:
                topicName = request.form["name"]
                cache.delete_memoized(cachedDbCalls.getAllTopics)

                topicImage = None
                if "photo" in request.files:
                    file = request.files["photo"]
                    if file.filename != "":
                        filename = photos.save(
                            request.files["photo"], name=str(uuid.uuid4()) + "."
                        )
                        topicImage = filename

                newTopic = topics.topics(topicName, topicImage)
                db.session.add(newTopic)

            # Initialize the Topic Cache
            topicQuery = cachedDbCalls.getAllTopics()
            for topic in topicQuery:
                globalvars.topicCache[topic.id] = topic.name

            db.session.commit()
            return redirect(url_for(".admin_page", page="topics"))

        elif settingType == "rtmpServer":
            address = request.form["address"]

            existingServer = settings.rtmpServer.query.filter_by(
                address=address
            ).first()

            if existingServer is None:
                newServer = settings.rtmpServer(address)
                db.session.add(newServer)
                db.session.commit()
                flash("Server Added", "success")
            else:
                flash("Server Already Exists", "error")

            return redirect(url_for(".admin_page", page="osprtmp"))

        elif settingType == "edgeNode":
            address = request.form["address"]
            port = request.form["edgePort"]
            loadPct = request.form["edgeLoad"]
            newEdge = settings.edgeStreamer(address, port, loadPct)

            try:
                edgeXML = requests.get("http://" + address + ":9000/stat").text
                edgeDict = xmltodict.parse(edgeXML)
                if "nginx_rtmp_version" in edgeDict["rtmp"]:
                    newEdge.status = 1
                    db.session.add(newEdge)
                    db.session.commit()
            except:
                newEdge.status = 0
                db.session.add(newEdge)
                db.session.commit()

            return redirect(url_for(".admin_page", page="ospedge"))

        elif settingType == "oAuthProvider":
            oAuth_type = request.form["oAuthPreset"]
            oAuth_name = request.form["oAuthName"]
            oAuth_friendlyName = request.form["oAuthFriendlyName"]
            oAuth_displayColor = request.form["oAuthColor"]
            oAuth_client_id = request.form["oAuthClient_id"]
            oAuth_client_secret = request.form["oAuthClient_secret"]
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
                oAuth_access_token_url = request.form["oAuthAccess_token_url"]
                oAuth_access_token_params = request.form["oAuthAccess_token_params"]
                oAuth_authorize_url = request.form["oAuthAuthorize_url"]
                oAuth_authorize_params = request.form["oAuthAuthorize_params"]
                oAuth_api_base_url = request.form["oAuthApi_base_url"]
                oAuth_client_kwargs = request.form["oAuthClient_kwargs"]
                oAuth_profile_endpoint = request.form["oAuthProfile_endpoint"]
                oAuth_id = request.form["oAuthIDValue"]
                oAuth_username = request.form["oAuthUsername"]
                oAuth_email = request.form["oAuthEmail"]
                if oAuth_access_token_params == "":
                    oAuth_access_token_params = None
                if oAuth_authorize_params == "":
                    oAuth_authorize_params = None
                if oAuth_client_kwargs == "":
                    oAuth_client_kwargs = None

            elif oAuth_type == "Discord":
                oAuth_access_token_url = "https://discordapp.com/api/oauth2/token"
                oAuth_authorize_url = "https://discordapp.com/api/oauth2/authorize"
                oAuth_api_base_url = "https://discordapp.com/api/"
                oAuth_client_kwargs = '{"scope":"identify email"}'
                oAuth_profile_endpoint = "users/@me"
                oAuth_id = "id"
                oAuth_username = "username"
                oAuth_email = "email"
            elif oAuth_type == "Reddit":
                oAuth_access_token_url = "https://www.reddit.com/api/v1/access_token"
                oAuth_authorize_url = "https://www.reddit.com/api/v1/authorize"
                oAuth_api_base_url = "https://oauth.reddit.com/api/v1/"
                oAuth_client_kwargs = '{"scope":"identity"}'
                oAuth_profile_endpoint = "me"
                oAuth_id = "id"
                oAuth_username = "name"
                oAuth_email = "email"
            elif oAuth_type == "Facebook":
                oAuth_access_token_url = (
                    "https://graph.facebook.com/v6.0/oauth/access_token"
                )
                oAuth_authorize_url = "https://graph.facebook.com/v6.0/oauth/authorize"
                oAuth_api_base_url = "https://graph.facebook.com/v6.0/"
                oAuth_client_kwargs = '{"scope": "email public_profile"}'
                oAuth_profile_endpoint = "me?fields=name,id,email"
                oAuth_id = "id"
                oAuth_username = "name"
                oAuth_email = "email"

            if request.form["oAuthID"] == "":
                newOauthProvider = settings.oAuthProvider(
                    oAuth_name,
                    oAuth_type,
                    oAuth_friendlyName,
                    oAuth_displayColor,
                    oAuth_client_id,
                    oAuth_client_secret,
                    oAuth_access_token_url,
                    oAuth_authorize_url,
                    oAuth_api_base_url,
                    oAuth_profile_endpoint,
                    oAuth_id,
                    oAuth_username,
                    oAuth_email,
                )
                if oAuth_access_token_params is not None:
                    newOauthProvider.access_token_params = oAuth_access_token_params
                if oAuth_authorize_params is not None:
                    newOauthProvider.authorize_params = oAuth_authorize_params
                if oAuth_client_kwargs is not None:
                    newOauthProvider.client_kwargs = oAuth_client_kwargs

                db.session.add(newOauthProvider)
                db.session.commit()

                provider = settings.oAuthProvider.query.filter_by(
                    name=oAuth_name
                ).first()

                oauth.register(
                    name=provider.name,
                    client_id=provider.client_id,
                    client_secret=provider.client_secret,
                    access_token_url=provider.access_token_url,
                    access_token_params=provider.access_token_params
                    if (
                        provider.access_token_params != ""
                        and provider.access_token_params is not None
                    )
                    else None,
                    authorize_url=provider.authorize_url,
                    authorize_params=provider.authorize_params
                    if (
                        provider.authorize_params != ""
                        and provider.authorize_params is not None
                    )
                    else None,
                    api_base_url=provider.api_base_url,
                    client_kwargs=json.loads(provider.client_kwargs)
                    if (
                        provider.client_kwargs != ""
                        and provider.client_kwargs is not None
                    )
                    else None,
                )
                globalvars.restartRequired = True
                flash("OAuth Provider Added", "success")

            else:
                existingOAuthID = request.form["oAuthID"]
                oAuthQuery = settings.oAuthProvider.query.filter_by(
                    id=int(existingOAuthID)
                ).first()
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

                    userQuery = Sec.User.query.filter_by(
                        oAuthProvider=oldOAuthName
                    ).all()
                    for user in userQuery:
                        user.oAuthProvider = oAuth_name
                    db.session.commit()

                    tokenQuery = Sec.OAuth2Token.query.filter_by(
                        name=oldOAuthName
                    ).all()
                    for token in tokenQuery:
                        token.name = oAuth_name
                    db.session.commit()

                    provider = settings.oAuthProvider.query.filter_by(
                        name=oAuth_name
                    ).first()

                    oauth.register(
                        name=provider.name,
                        overwrite=True,
                        client_id=provider.client_id,
                        client_secret=provider.client_secret,
                        access_token_url=provider.access_token_url,
                        access_token_params=provider.access_token_params
                        if (
                            provider.access_token_params != ""
                            and provider.access_token_params is not None
                        )
                        else None,
                        authorize_url=provider.authorize_url,
                        authorize_params=provider.authorize_params
                        if (
                            provider.authorize_params != ""
                            and provider.authorize_params is not None
                        )
                        else None,
                        api_base_url=provider.api_base_url,
                        client_kwargs=json.loads(provider.client_kwargs)
                        if (
                            provider.client_kwargs != ""
                            and provider.client_kwargs is not None
                        )
                        else None,
                    )
                    globalvars.restartRequired = True
                    flash("OAuth Provider Updated", "success")
                else:
                    flash("OAuth Provider Does Not Exist", "error")

            return redirect(url_for(".admin_page", page="oauth"))

        elif settingType == "DeleteOAuthProvider":
            oAuthProvider = request.form["DeleteOAuthProviderID"]

            oAuthProviderQuery = settings.oAuthProvider.query.filter_by(
                id=int(oAuthProvider)
            ).first()
            if oAuthProvider is not None:
                userQuery = Sec.User.query.filter_by(
                    oAuthProvider=oAuthProviderQuery.name, authType=1
                ).all()
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
                globalvars.restartRequired = True
                flash(
                    "OAuth Provider Deleted - "
                    + str(count)
                    + " User(s) Converted to Local Users",
                    "success",
                )
            else:
                flash("Invalid OAuth Object", "error")
            return redirect(url_for(".admin_page", page="oauth"))

        elif settingType == "newuser":

            password = request.form["password1"]
            emailAddress = request.form["emailaddress"]
            username = request.form["username"]

            # Check for Existing Users
            existingUserQuery = Sec.User.query.filter_by(username=username).first()
            if existingUserQuery is not None:
                flash("A user already exists with this username", "error")
                db.session.commit()
                return redirect(url_for(".admin_page", page="users"))

            existingUserQuery = Sec.User.query.filter_by(email=emailAddress).first()
            if existingUserQuery is not None:
                flash("A user already exists with this email address", "error")
                db.session.commit()
                return redirect(url_for(".admin_page", page="users"))

            passwordhash = hash_password(password)

            user_datastore.create_user(
                email=emailAddress, username=username, password=passwordhash
            )
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
            return redirect(url_for(".admin_page", page="users"))

        elif settingType == "panel":
            panelName = request.form["panel-name"]
            panelType = int(request.form["panel-type"])
            panelHeader = request.form["panel-header"]
            panelContent = request.form["panel-content"]
            globalPanelId = request.form["PanelId"]

            panelOrder = 0
            if panelType != 0:
                if "panel-order" in request.form:
                    panelOrder = int(request.form["panel-order"])

            if globalPanelId == "":
                newGlobalPanel = panel.globalPanel(
                    panelName, panelType, panelHeader, panelOrder, panelContent
                )
                db.session.add(newGlobalPanel)
                db.session.commit()
            else:
                globalPanelId = int(globalPanelId)
                existingPanel = panel.globalPanel.query.filter_by(
                    id=globalPanelId
                ).first()
                if existingPanel is not None:
                    existingPanel.name = panelName
                    existingPanel.type = panelType
                    existingPanel.header = panelHeader
                    existingPanel.order = panelOrder
                    existingPanel.content = panelContent
                    cache.delete_memoized(cachedDbCalls.getGlobalPanel, globalPanelId)
                    db.session.commit()
            return redirect(url_for(".admin_page", page="settings"))

        return redirect(url_for(".admin_page"))


@admin_settings_bp.route("/action/<string:action>")
@login_required
@roles_required("Admin")
def admin_action(action):
    setting = request.args.get("setting")

    if action == "delete":
        if setting == "topics":
            topicID = int(request.args.get("topicID"))

            topicQuery = topics.topics.query.filter_by(id=topicID).first()

            channels = Channel.Channel.query.filter_by(topic=topicID).all()
            videos = RecordedVideo.RecordedVideo.query.filter_by(
                topic=topicID
            ).all()

            defaultTopic = topics.topics.query.filter_by(name="Other").first()

            for chan in channels:
                chan.topic = defaultTopic.id
            for vid in videos:
                vid.topic = defaultTopic.id

            system.newLog(
                1,
                "User "
                + current_user.username
                + " deleted Topic "
                + str(topicQuery.name),
            )
            db.session.delete(topicQuery)
            db.session.commit()
            cache.delete_memoized(cachedDbCalls.getAllTopics)

            # Initialize the Topic Cache
            topicQuery = cachedDbCalls.getAllTopics()
            for topic in topicQuery:
                globalvars.topicCache[topic.id] = topic.name

            flash("Topic Deleted")
            return redirect(url_for(".admin_page", page="topics"))

        elif setting == "users":
            userID = int(request.args.get("userID"))

            if current_user.id == userID:
                flash("User cannot delete self", "Error")
                return redirect(url_for(".admin_page", page="users"))

            userQuery = Sec.User.query.filter_by(id=userID).first()

            if userQuery is not None:

                securityFunc.delete_user(userQuery.id)

                flash("User " + str(userQuery.username) + " Deleted")

                return redirect(url_for(".admin_page", page="users"))

        elif setting == "userRole":
            userID = int(request.args.get("userID"))
            if current_user.id == userID:
                flash("User cannot delete own roles", "Error")
                return redirect(url_for(".admin_page"))

            roleID = int(request.args.get("roleID"))

            userQuery = Sec.User.query.filter_by(id=userID).first()
            roleQuery = Sec.Role.query.filter_by(id=roleID).first()

            if userQuery is not None and roleQuery is not None:
                user_datastore.remove_role_from_user(userQuery, roleQuery.name)
                db.session.commit()
                system.newLog(
                    1,
                    "User "
                    + current_user.username
                    + " Removed Role "
                    + roleQuery.name
                    + " from User"
                    + userQuery.username,
                )
                if roleQuery.name == 'GlobalChatMod':
                    cachedDbCalls.invalidateGCMCache(userQuery.uuid)
                    channel_tasks.remove_global_chat_mod_from_channels.delay(userQuery.id, userQuery.uuid)
                flash("Removed Role from User")

            else:
                flash("Invalid Role or User!")
            return redirect(url_for(".admin_page", page="users"))

    elif action == "add":
        if setting == "userRole":
            userID = int(request.args.get("userID"))
            roleName = str(request.args.get("roleName"))

            userQuery = Sec.User.query.filter_by(id=userID).first()
            roleQuery = Sec.Role.query.filter_by(name=roleName).first()

            if userQuery is not None and roleQuery is not None:
                user_datastore.add_role_to_user(userQuery, roleQuery.name)
                db.session.commit()
                system.newLog(
                    1,
                    "User "
                    + current_user.username
                    + " Added Role "
                    + roleQuery.name
                    + " to User "
                    + userQuery.username,
                )
                if roleName == 'GlobalChatMod':
                    cachedDbCalls.invalidateGCMCache(userQuery.uuid)
                    channel_tasks.add_new_global_chat_mod_to_channels.delay(userQuery.id, userQuery.uuid)
                flash("Added Role to User")
            else:
                flash("Invalid Role or User!")
            return redirect(url_for(".admin_page", page="users"))
    elif action == "toggleActive":
        if setting == "users":
            userID = int(request.args.get("userID"))

            if current_user.id == userID:
                flash("User cannot disable/enable self", "Error")
                return redirect(url_for(".admin_page", page="users"))

            userQuery = Sec.User.query.filter_by(id=userID).first()
            if userQuery is not None:
                if userQuery.active:
                    userQuery.active = False
                    system.newLog(
                        1,
                        "User "
                        + current_user.username
                        + " Disabled User "
                        + userQuery.username,
                    )
                    flash("User Disabled")
                else:
                    userQuery.active = True
                    deletionFlagQuery = (
                        Sec.UsersFlaggedForDeletion.query.filter_by(
                            userID=userID
                        ).all()
                    )
                    for flag in deletionFlagQuery:
                        db.session.delete(flag)
                    system.newLog(
                        1,
                        "User "
                        + current_user.username
                        + " Enabled User "
                        + userQuery.username,
                    )
                    flash("User Enabled")
                db.session.commit()
            return redirect(url_for(".admin_page", page="users"))

    return redirect(url_for(".admin_page"))


@admin_settings_bp.route("/create_test_task")
@login_required
@roles_required("Admin")
def createtestask():
    result = system.testCelery.apply_async(countdown=1)
    return str(result)


@admin_settings_bp.route("/run_task/<task>")
@login_required
@roles_required("Admin")
def run_task(task):
    if task == "process_ingest":
        result = video_tasks.process_ingest_folder.delay()
    elif task == "reprocess_stuck_videos":
        result = video_tasks.reprocess_stuck_videos.delay()
    elif task == "check_video_published_exists":
        result = video_tasks.check_video_published_exists.delay()
    elif task == "check_video_retention":
        result = video_tasks.check_video_retention.delay()
    elif task == "check_clip_retention":
        result = video_tasks.check_video_retention.delay(checkVideos=False, checkClips=True)
    elif task == "check_video_and_clip_retention":
        result = video_tasks.check_video_retention.delay(checkVideos=True, checkClips=True)
    elif task == "check_video_thumbnails":
        result = video_tasks.check_video_thumbnails.delay()
    else:
        result = False
    return str(result)


@admin_settings_bp.route("/rtmpstat/<node>")
@login_required
@roles_required("Admin")
def rtmpStat_page(node):
    r = None
    if node == "localhost":
        r = requests.get("http://127.0.0.1:9000/stat").text
    else:
        nodeQuery = settings.edgeStreamer.query.filter_by(address=node).first()
        if nodeQuery is not None:
            r = requests.get("http://" + nodeQuery.address + ":9000/stat").text

    if r is not None:
        data = None
        try:
            data = xmltodict.parse(r)
            data = json.dumps(data)
        except:
            return abort(500)
        return data
    return abort(500)


@admin_settings_bp.route("/features")
@login_required
@roles_required("Admin")
def admin_devFeatures():
    return render_template(themes.checkOverride("devfeatures.html"))
