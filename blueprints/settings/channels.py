import os
import json
import uuid
import re
import bleach
import xmlrpc.client

from flask import (
    request,
    flash,
    render_template,
    redirect,
    url_for,
    Blueprint,
    current_app,
    session,
)
from flask_security import (
    current_user,
    login_required,
    roles_required,
)

from classes.shared import db
from classes import Channel
from classes import topics
from classes import settings
from classes import views
from classes import stickers
from classes import panel
from classes import Sec
from classes.shared import cache

from functions import system
from functions import themes
from functions import cachedDbCalls
from functions import xmpp
from functions.scheduled_tasks import channel_tasks

from globals import globalvars

from app import photos
from app import stickerUploads


channel_settings_bp = Blueprint("channel_settings", __name__, url_prefix="/channels")

@channel_settings_bp.route("/", methods=["POST", "GET"])
@login_required
@roles_required("Streamer")
def settings_channels_page():
    sysSettings = cachedDbCalls.getSystemSettings()

    videos_root = current_app.config["WEB_ROOT"] + "videos/"
    if request.method == "GET":
        topicList = cachedDbCalls.getAllTopics()
        user_channels = (
            Channel.Channel.query.filter_by(owningUser=current_user.id)
            .with_entities(
                Channel.Channel.id,
                Channel.Channel.channelName,
                Channel.Channel.channelLoc,
                Channel.Channel.topic,
                Channel.Channel.views,
                Channel.Channel.streamKey,
                Channel.Channel.protected,
                Channel.Channel.private,
                Channel.Channel.showHome,
                Channel.Channel.xmppToken,
                Channel.Channel.chatEnabled,
                Channel.Channel.autoPublish,
                Channel.Channel.allowComments,
                Channel.Channel.record,
                Channel.Channel.description,
                Channel.Channel.offlineImageLocation,
                Channel.Channel.channelBannerLocation,
                Channel.Channel.imageLocation,
                Channel.Channel.vanityURL,
                Channel.Channel.maxVideoRetention,
                Channel.Channel.maxClipRetention,
                Channel.Channel.defaultStreamName,
                Channel.Channel.allowGuestNickChange,
                Channel.Channel.showChatJoinLeaveNotification,
                Channel.Channel.chatFormat,
                Channel.Channel.chatHistory,
                Channel.Channel.hubEnabled,
                Channel.Channel.hubNSFW
            )
            .all()
        )

        activeRTMPQuery = settings.rtmpServer.query.filter_by(
            active=True, hide=False
        ).all()
        activeRTMPList = []
        for server in activeRTMPQuery:
            address = server.address
            if address == "127.0.0.1" or address == "localhost":
                address = sysSettings.siteAddress
            if address not in activeRTMPList:
                activeRTMPList.append(address)

        # Get xmpp room options
        from app import ejabberd

        gcm_users = Sec.Role.query.filter_by(
            name="GlobalChatMod"
        ).one().users.with_entities(
            Sec.User.uuid,
            Sec.User.username,
        )
        channelRooms = {}
        channelMods = {}
        for chan in user_channels:
            try:
                xmppQuery = ejabberd.get_room_options(
                    chan.channelLoc, "conference." + globalvars.defaultChatDomain
                )
                xmppQuery = ejabberd.get_room_affiliations(
                    chan.channelLoc, "conference." + globalvars.defaultChatDomain
                )
            except (AttributeError, xmlrpc.client.Fault):
                # If Channel Doesn't Exist in ejabberd, Create
                try:
                    xmpp.buildRoom(
                        chan.channelLoc,
                        current_user.uuid,
                        channel_title=chan.channelName,
                        channel_desc=current_user.username + 's chat room for the channel "' + chan.channelName + '"'
                    )
                except:
                    # Attempting to create a chat-room that already exists...
                    # raises a "Room Already Exists" xmlrpc.client.Fault.
                    pass
            except:
                # Try again if request causes strange "http.client.CannotSendRequest: Request-sent" Error
                return redirect(url_for(".settings_channels_page"))

            channelRooms[chan.channelLoc] = xmpp.getChannelOptions(chan.channelLoc)

            # Get room affiliations
            xmppQuery = ejabberd.get_room_affiliations(
                chan.channelLoc, "conference." + globalvars.defaultChatDomain
            )

            affiliationList = []
            for affiliation in xmppQuery["affiliations"]:
                user = {}
                for entry in affiliation["affiliation"]:
                    for key, value in entry.items():
                        user[key] = value
                affiliationList.append(user)

            channelModList = []
            for user in affiliationList:
                if (
                    user["affiliation"] == "admin" and
                    gcm_users.filter_by(uuid=user['username']).first() is None
                ):
                    channelModList.append(user["username"] + "@" + user["domain"])
            channelMods[chan.channelLoc] = channelModList

        # Calculate Channel Views by Date based on Video or Live Views and Generate Chanel Panel Ordering
        user_channels_stats = {}
        channelPanelOrder = {}
        for channel in user_channels:

            # 30 Days Viewer Stats
            viewersTotal = 0

            statsViewsLiveDay = cachedDbCalls.getChannelLiveViewsByDate(channel.id)
            statsViewsLiveDayArray = []
            for entry in statsViewsLiveDay:
                viewersTotal = viewersTotal + entry[1]
                statsViewsLiveDayArray.append({"t": (entry[0]), "y": entry[1]})

            statsViewsRecordedDayDict = {}
            statsViewsRecordedDayArray = []

            recordedVidsQuery = cachedDbCalls.getChannelVideos(channel.id)

            for vid in recordedVidsQuery:
                statsViewsRecordedDay = cachedDbCalls.getVideoViewsByDate(vid.id)

                for entry in statsViewsRecordedDay:
                    if entry[0] in statsViewsRecordedDayDict:
                        statsViewsRecordedDayDict[entry[0]] = (
                            statsViewsRecordedDayDict[entry[0]] + entry[1]
                        )
                    else:
                        statsViewsRecordedDayDict[entry[0]] = entry[1]
                    viewersTotal = viewersTotal + entry[1]

            for entry in statsViewsRecordedDayDict:
                statsViewsRecordedDayArray.append(
                    {"t": entry, "y": statsViewsRecordedDayDict[entry]}
                )

            sortedStatsArray = sorted(statsViewsRecordedDayArray, key=lambda d: d["t"])

            statsViewsDay = {
                "live": statsViewsLiveDayArray,
                "recorded": sortedStatsArray,
            }

            user_channels_stats[channel.id] = statsViewsDay

            channelPanelOrderMappingQuery = panel.panelMapping.query.filter_by(
                panelType=2, panelLocationId=channel.id
            ).all()
            ChannelPanelOrderArray = []
            for panelEntry in channelPanelOrderMappingQuery:
                ChannelPanelOrderArray.append(panelEntry)
            channelPanelOrder[channel.id] = sorted(
                ChannelPanelOrderArray, key=lambda x: x.panelOrder
            )

        return render_template(
            themes.checkOverride("user_channels.html"),
            channels=user_channels,
            topics=topicList,
            channelRooms=channelRooms,
            gcm_users=gcm_users.all(),
            channelMods=channelMods,
            viewStats=user_channels_stats,
            rtmpList=activeRTMPList,
            channelPanelMapping=channelPanelOrder,
        )
    elif request.method == "POST":
        requestType = None

        # Workaround check if we are now using a modal originally for Admin/Global
        if "type" in request.form:
            requestType = request.form["type"]
        elif "settingType" in request.form:
            requestType = request.form["settingType"]

        # Process New Stickers
        if requestType == "newSticker":
            if "stickerChannelID" in request.form:
                channelQuery = cachedDbCalls.getChannel(
                    int(request.form["stickerChannelID"])
                )
                if (
                    channelQuery is not None
                    and current_user.id == channelQuery.owningUser
                ):
                    if "stickerName" in request.form:
                        stickerName = request.form["stickerName"]
                        existingStickerNameQuery = stickers.stickers.query.filter_by(
                                                    name=stickerName,
                                                    channelID=channelQuery.id
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
                                        return redirect(url_for(".settings_channels_page"))

                                    fileName = stickerUploads.save(
                                        request.files["stickerUpload"],
                                        name=stickerName + ".",
                                        folder="stickers/" + channelQuery.channelLoc,
                                    )
                                    fileName = fileName.replace(
                                        "stickers/" + channelQuery.channelLoc + "/", ""
                                    )
                                    newSticker = stickers.stickers(
                                        stickerName, fileName
                                    )
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
            return redirect(url_for(".settings_channels_page"))
        elif requestType == "panel":
            panelName = request.form["panel-name"]
            panelType = int(request.form["panel-type"])
            panelHeader = request.form["panel-header"]
            panelContent = request.form["panel-content"]
            PanelId = request.form["PanelId"]
            panelChannelId = int(request.form["PanelLocationId"])

            channelQuery = cachedDbCalls.getChannel(panelChannelId)
            if channelQuery is not None and channelQuery.owningUser == current_user.id:

                panelOrder = 0
                if panelType != 0:
                    if "panel-order" in request.form:
                        panelOrder = int(request.form["panel-order"])

                if PanelId == "":
                    newChannellPanel = panel.channelPanel(
                        panelName,
                        channelQuery.id,
                        panelType,
                        panelHeader,
                        panelOrder,
                        panelContent,
                    )
                    db.session.add(newChannellPanel)
                    db.session.commit()
                    flash("New Channel Panel Added", "Success")
                else:
                    existingPanel = panel.channelPanel.query.filter_by(
                        id=PanelId, channelId=channelQuery.id
                    ).first()
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
                return redirect(url_for(".settings_channels_page"))
            else:
                flash("Invalid Channel", "Error")
                return redirect(url_for(".settings_channels_page"))

        channelName = system.strip_html(request.form["channelName"])
        topic = request.form["channeltopic"]
        description = bleach.clean(system.strip_html(request.form["description"]))

        record = False

        if "recordSelect" in request.form and sysSettings.allowRecording is True:
            record = True

        autoPublish = False
        if "publishSelect" in request.form:
            autoPublish = True

        chatEnabled = False

        if "chatSelect" in request.form:
            chatEnabled = True

        allowComments = False

        if "allowComments" in request.form:
            allowComments = True

        protection = False

        if "channelProtection" in request.form:
            protection = True

        showHome = False

        if "showHome" in request.form:
            showHome = True

        private = False

        if "private" in request.form:
            private = True

        hubPublish = False
        if "hubPublishSelect" in request.form:
            hubPublish = True
        
        hubNSFW = False
        if "hubNSFWSelect" in request.form:
            hubNSFW = True

        if requestType == "new":
            # Check Maximum Channel Limit
            if (
                sysSettings.limitMaxChannels != 0
                and current_user.has_role("Admin") is False
            ):
                channelCount = Channel.Channel.query.filter_by(
                    owningUser=current_user.id
                ).count()
                if channelCount >= sysSettings.limitMaxChannels:
                    flash(
                        "Maximum Number of Channels Allowed Reached - Limit: "
                        + str(sysSettings.limitMaxChannels),
                        "error",
                    )
                    db.session.commit()
                    return redirect(url_for(".settings_channels_page"))

            newUUID = str(uuid.uuid4())

            newChannel = Channel.Channel(
                current_user.id,
                newUUID,
                channelName,
                topic,
                record,
                chatEnabled,
                allowComments,
                showHome,
                description,
            )

            if "photo" in request.files:
                file = request.files["photo"]
                if file.filename != "":
                    filename = photos.save(
                        request.files["photo"], name=str(uuid.uuid4()) + "."
                    )
                    newChannel.imageLocation = filename

            # Establish XMPP Channel
            xmpp.buildRoom(
                newChannel.channelLoc,
                current_user.uuid,
                channel_title=newChannel.channelName,
                channel_desc=current_user.username + 's chat room for the channel "' + newChannel.channelName + '"'
            )

            db.session.add(newChannel)
            db.session.commit()

            channel_tasks.new_channel_assign_global_chat_mods.delay(current_user.id, newChannel.channelLoc)

        elif requestType == "change":
            channelId = request.form["channelId"]

            defaultstreamName = request.form["channelStreamName"]

            requestedChannel = cachedDbCalls.getChannel(channelId)

            if current_user.id == requestedChannel.owningUser:

                if "channelTags" in request.form:
                    channelTagString = request.form["channelTags"]
                    tagArray = system.parseTags(channelTagString)
                    existingTagArray = Channel.channel_tags.query.filter_by(
                        channelID=channelId
                    ).all()

                    for currentTag in existingTagArray:
                        if currentTag.name not in tagArray:
                            db.session.delete(currentTag)
                        else:
                            tagArray.remove(currentTag.name)
                    db.session.commit()
                    for currentTag in tagArray:
                        newTag = Channel.channel_tags(
                            currentTag, channelId, current_user.id
                        )
                        db.session.add(newTag)
                        db.session.commit()
                
                updateDict = dict(
                    channelName=channelName,
                    topic=topic,
                    record=record,
                    chatEnabled=chatEnabled,
                    allowComments=allowComments,
                    showHome=showHome,
                    description=description,
                    protected=protection,
                    defaultStreamName=defaultstreamName,
                    autoPublish=autoPublish,
                    private=private,
                    hubEnabled = hubPublish,
                    hubNSFW = hubNSFW
                )

                if "vanityURL" in request.form:
                    requestedVanityURL = re.sub("[^A-Za-z0-9]+", "", request.form["vanityURL"][:32])
                    if requestedVanityURL != "":
                        existingChannelQuery = Channel.Channel.query.filter_by(
                            vanityURL=requestedVanityURL
                        ).with_entities(Channel.Channel.id).first()
                        if (
                            existingChannelQuery is None
                            or existingChannelQuery.id == channelId
                        ):
                            updateDict['vanityURL'] = requestedVanityURL
                        else:
                            flash(
                                "Short link not saved. Link with same name exists!",
                                "error",
                            )
                    else:
                        updateDict['vanityURL'] = None

                if 'maxVideoRetention' in request.form:
                    updateDict['maxVideoRetention'] = max(0, int(request.form['maxVideoRetention']))

                if 'maxClipRetention' in request.form:
                    updateDict['maxClipRetention'] = max(0, int(request.form['maxClipRetention']))

                from app import ejabberd

                if protection is True:
                    ejabberd.change_room_option(
                        requestedChannel.channelLoc,
                        "conference." + globalvars.defaultChatDomain,
                        "password_protected",
                        "true",
                    )
                    ejabberd.change_room_option(
                        requestedChannel.channelLoc,
                        "conference." + globalvars.defaultChatDomain,
                        "password",
                        requestedChannel.xmppToken,
                    )
                else:
                    ejabberd.change_room_option(
                        requestedChannel.channelLoc,
                        "conference." + globalvars.defaultChatDomain,
                        "password",
                        "",
                    )
                    ejabberd.change_room_option(
                        requestedChannel.channelLoc,
                        "conference." + globalvars.defaultChatDomain,
                        "password_protected",
                        "false",
                    )

                if "photo" in request.files:
                    file = request.files["photo"]
                    if file.filename != "":
                        oldImage = None

                        if requestedChannel.imageLocation is not None:
                            oldImage = requestedChannel.imageLocation

                        filename = photos.save(
                            request.files["photo"], name=str(uuid.uuid4()) + "."
                        )
                        updateDict["imageLocation"] = filename

                        if oldImage is not None:
                            try:
                                os.remove(oldImage)
                            except OSError:
                                pass

                if "offlinephoto" in request.files:
                    file = request.files["offlinephoto"]
                    if file.filename != "":
                        oldImage = None

                        if requestedChannel.offlineImageLocation is not None:
                            oldImage = requestedChannel.offlineImageLocation

                        filename = photos.save(
                            request.files["offlinephoto"], name=str(uuid.uuid4()) + "."
                        )
                        updateDict["offlineImageLocation"] = filename

                        if oldImage is not None:
                            try:
                                os.remove(oldImage)
                            except OSError:
                                pass

                # CHANNEL BANNER
                if "channelbannerphoto" in request.files:
                    file = request.files["channelbannerphoto"]
                    if file.filename != "":
                        oldImage = None

                        if requestedChannel.channelBannerLocation is not None:
                            oldImage = requestedChannel.channelBannerLocation

                        filename = photos.save(
                            request.files["channelbannerphoto"], name=str(uuid.uuid4()) + "."
                        )
                        updateDict["channelBannerLocation"] = filename

                        if oldImage is not None:
                            try:
                                os.remove(oldImage)
                            except OSError:
                                pass

                channelUpdateQuery = Channel.Channel.query.filter_by(
                    id=channelId
                ).update(updateDict)

                # Invalidate Channel Cache
                cachedDbCalls.invalidateChannelCache(channelId)

                flash("Channel Saved")
                db.session.commit()
            else:
                flash("Invalid Change Attempt", "Error")
            return redirect(url_for(".settings_channels_page"))
        return redirect(url_for(".settings_channels_page"))

@channel_settings_bp.route("/streamKey", methods=["POST"])
@login_required
@roles_required("Streamer")
def settings_channel_new_stream_key():
    channelId = request.json['channelId']

    requestedChannel = cachedDbCalls.getChannel(channelId)

    returnPayload = {
        'result': None, 'error': None
    }
    if current_user.id != requestedChannel.owningUser:
        returnPayload['error'] = "Invalid Stream Key Change Attempt"
        return returnPayload

    try:
        newStreamKey = str(uuid.uuid4())
        updateDict = dict(
            streamKey=newStreamKey,
        )
        channelUpdateQuery = Channel.Channel.query.filter_by(
            id=channelId
        ).update(updateDict)
        cachedDbCalls.invalidateChannelCache(channelId)
        db.session.commit()

        returnPayload['result'] = newStreamKey
    except Exception as e:
        returnPayload['error'] = "Failed to update stream key"
    finally:
        return returnPayload

@channel_settings_bp.route("/chat", methods=["POST", "GET"])
@login_required
@roles_required("Streamer")
def settings_channels_chat_page():
    sysSettings = cachedDbCalls.getSystemSettings()

    if request.method == "POST":
        from app import ejabberd

        channelLoc = system.strip_html(request.form["channelLoc"])
        channelQuery = cachedDbCalls.getChannelByLoc(request.form["channelLoc"])
        if channelQuery is not None and current_user.id == channelQuery.owningUser:
            roomTitle = request.form["roomTitle"]
            roomDescr = system.strip_html(request.form["roomDescr"])
            ejabberd.change_room_option(
                channelLoc, "conference." + globalvars.defaultChatDomain, "title", roomTitle
            )
            ejabberd.change_room_option(
                channelLoc,
                "conference." + globalvars.defaultChatDomain,
                "description",
                roomDescr,
            )

            chatFormat = request.form["chatFormat"]

            chatHistory = request.form["chatHistory"]

            if "moderatedSelect" in request.form:
                ejabberd.change_room_option(
                    channelLoc,
                    "conference." + globalvars.defaultChatDomain,
                    "moderated",
                    "true",
                )
            else:
                ejabberd.change_room_option(
                    channelLoc,
                    "conference." + globalvars.defaultChatDomain,
                    "moderated",
                    "false",
                )

            if "allowGuests" in request.form:
                ejabberd.change_room_option(
                    channelLoc,
                    "conference." + globalvars.defaultChatDomain,
                    "members_only",
                    "false",
                )
            else:
                ejabberd.change_room_option(
                    channelLoc,
                    "conference." + globalvars.defaultChatDomain,
                    "members_only",
                    "true",
                )

            if "allowGuestsChat" in request.form:
                ejabberd.change_room_option(
                    channelLoc,
                    "conference." + globalvars.defaultChatDomain,
                    "members_by_default",
                    "true",
                )
            else:
                ejabberd.change_room_option(
                    channelLoc,
                    "conference." + globalvars.defaultChatDomain,
                    "members_by_default",
                    "false",
                )
            
            allowGuestNickChange = False
            if "allowGuestsNickChange" in request.form:
                allowGuestNickChange = True

            showChatJoinLeaveNotification = False
            if "showJoinPartMsg" in request.form:
                showChatJoinLeaveNotification = True
            
            channelUpdate = (
                Channel.Channel.query.filter_by(id=channelQuery.id)
                .update(
                    dict(
                        allowGuestNickChange=allowGuestNickChange,
                        showChatJoinLeaveNotification=showChatJoinLeaveNotification,
                        chatFormat=chatFormat,
                        chatHistory=chatHistory
                    )
                )
            )
            db.session.commit()
            cachedDbCalls.invalidateChannelCache(channelQuery.id)

    return redirect(url_for(".settings_channels_page"))
