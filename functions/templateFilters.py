from urllib.parse import urlparse
import time
import datetime
import os
import pytz
import random
import string

from flask_security import current_user
from sqlalchemy import func
import hashlib

from globals import globalvars

from classes import Sec
from classes import comments
from classes import panel
from classes import Stream
from classes import settings
from classes import RecordedVideo
from classes import Channel
from classes import invites
from classes import webhook
from classes import stickers

from functions import votes
from functions import cachedDbCalls


def init(context):
    context.jinja_env.filters["generateRandomString"] = generateRandomString
    context.jinja_env.filters["normalize_uuid"] = normalize_uuid
    context.jinja_env.filters["normalize_urlroot"] = normalize_urlroot
    context.jinja_env.filters["normalize_url"] = normalize_url
    context.jinja_env.filters["normalize_date"] = normalize_date
    context.jinja_env.filters["limit_title"] = limit_title
    context.jinja_env.filters["limit_title20"] = limit_title20
    context.jinja_env.filters["format_kbps"] = format_kbps
    context.jinja_env.filters["hms_format"] = hms_format
    context.jinja_env.filters["get_topicName"] = get_topicName
    context.jinja_env.filters["get_userName"] = get_userName
    context.jinja_env.filters["get_channelSubCount"] = get_channelSubCount
    context.jinja_env.filters["get_Video_Upvotes"] = get_Video_Upvotes_Filter
    context.jinja_env.filters["get_Stream_Upvotes"] = get_Stream_Upvotes_Filter
    context.jinja_env.filters["get_Clip_Upvotes"] = get_Clip_Upvotes_Filter
    context.jinja_env.filters["get_Video_Comments"] = get_Video_Comments_Filter
    context.jinja_env.filters["get_pictureLocation"] = get_pictureLocation
    context.jinja_env.filters["get_diskUsage"] = get_diskUsage
    context.jinja_env.filters["testList"] = testList
    context.jinja_env.filters["get_webhookTrigger"] = get_webhookTrigger
    context.jinja_env.filters["get_logType"] = get_logType
    context.jinja_env.filters["format_clipLength"] = format_clipLength
    context.jinja_env.filters["processClientCount"] = processClientCount
    context.jinja_env.filters["formatSpace"] = formatSpace
    context.jinja_env.filters["uuid_to_username"] = uuid_to_username
    context.jinja_env.filters["format_keyType"] = format_keyType
    context.jinja_env.filters["get_channelLiveStatus"] = get_channelLiveStatus
    context.jinja_env.filters["get_channelPrivateStatus"] = get_channelPrivateStatus
    context.jinja_env.filters["get_channelName"] = get_channelName
    context.jinja_env.filters["get_clipTags"] = get_clipTags
    context.jinja_env.filters["get_clipTags_csv"] = get_clipTags_csv
    context.jinja_env.filters["get_videoTags"] = get_videoTags
    context.jinja_env.filters["get_videoTags_csv"] = get_videoTags_csv
    context.jinja_env.filters["get_videoComments"] = get_videoComments
    context.jinja_env.filters["get_channelTags"] = get_channelTags
    context.jinja_env.filters["get_channelTags_csv"] = get_channelTags_csv
    context.jinja_env.filters["get_channelProtected"] = get_channelProtected
    context.jinja_env.filters["get_channelLocationFromID"] = get_channelLocationFromID
    context.jinja_env.filters["channeltoOwnerID"] = channeltoOwnerID
    context.jinja_env.filters["videotoChannelID"] = videotoChannelID
    context.jinja_env.filters["get_channelTopic"] = get_channelTopic
    context.jinja_env.filters["get_videoTopic"] = get_videoTopic
    context.jinja_env.filters["get_videoDate"] = get_videoDate
    context.jinja_env.filters["get_channelPicture"] = get_channelPicture
    context.jinja_env.filters["is_channelObjVisible"] = is_channelObjVisible
    context.jinja_env.filters["localize_time"] = localize_time
    context.jinja_env.filters["epoch_to_datetime"] = epoch_to_datetime
    context.jinja_env.filters["convert_mins"] = convert_mins
    context.jinja_env.filters["globalPanelIdToPanelName"] = globalPanelIdToPanelName
    context.jinja_env.filters["channelPanelIdToPanelName"] = channelPanelIdToPanelName
    context.jinja_env.filters[
        "panelOrderIdToPanelOrderName"
    ] = panelOrderIdToPanelOrderName
    context.jinja_env.filters["panelTypeIdToPanelTypeName"] = panelTypeIdToPanelTypeName
    context.jinja_env.filters["getLiveStream"] = getLiveStream
    context.jinja_env.filters["getLiveStreamURL"] = getLiveStreamURL
    context.jinja_env.filters["getGlobalPanelArg"] = getGlobalPanelArg
    context.jinja_env.filters["getPanel"] = getPanel
    context.jinja_env.filters["getChannelPanels"] = getChannelPanels
    context.jinja_env.filters["orderVideoBy"] = orderVideoBy
    context.jinja_env.filters["getPanelStreamList"] = getPanelStreamList
    context.jinja_env.filters["getPanelVideoList"] = getPanelVideoList
    context.jinja_env.filters["getPanelClipList"] = getPanelClipList
    context.jinja_env.filters["getPanelChannelList"] = getPanelChannelList
    context.jinja_env.filters["generatePlaybackAuthToken"] = generatePlaybackAuthToken
    context.jinja_env.filters["get_channelInviteCodes"] = get_channelInviteCodes
    context.jinja_env.filters["get_channelInvitedUsers"] = get_channelInvitedUsers
    context.jinja_env.filters[
        "get_channelRestreamDestinations"
    ] = get_channelRestreamDestinations
    context.jinja_env.filters["get_channelWebhooks"] = get_channelWebhooks
    context.jinja_env.filters["get_channelVideos"] = get_channelVideos
    context.jinja_env.filters["get_channelClips"] = get_channelClips
    context.jinja_env.filters["get_flaggedForDeletion"] = get_flaggedForDeletion
    context.jinja_env.filters["get_channelData"] = get_channelData
    context.jinja_env.filters["get_channelStickers"] = get_channelStickers


# ----------------------------------------------------------------------------#
# Template Filters
# ----------------------------------------------------------------------------#


def generateRandomString(x):
    letters = string.ascii_lowercase
    randomString = "".join(random.choice(letters) for i in range(10))
    return randomString


def normalize_uuid(uuidstr):
    return uuidstr.replace("-", "")


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


def normalize_url(urlString):
    parsedURL = urlparse(urlString)
    if parsedURL.port == 80:
        URLProtocol = "http"
    elif parsedURL.port == 443:
        URLProtocol = "https"
    else:
        URLProtocol = parsedURL.scheme
    reparsedString = (
        str(URLProtocol) + "://" + str(parsedURL.hostname) + str(parsedURL.path)
    )
    return str(reparsedString)


def normalize_date(dateStr):
    return str(dateStr)[:16]


def limit_title(titleStr):
    if len(titleStr) > 40:
        return titleStr[:37] + "..."
    else:
        return titleStr


def limit_title20(titleStr):
    if len(titleStr) > 20:
        return titleStr[:17] + "..."
    else:
        return titleStr


def formatSpace(B):
    "Return the given bytes as a human friendly KB, MB, GB, or TB string"
    B = float(B)
    KB = float(1024)
    MB = float(KB**2)  # 1,048,576
    GB = float(KB**3)  # 1,073,741,824
    TB = float(KB**4)  # 1,099,511,627,776

    if B < KB:
        return "{0} {1}".format(B, "Bytes" if 0 == B > 1 else "Byte")
    elif KB <= B < MB:
        return "{0:.2f} KB".format(B / KB)
    elif MB <= B < GB:
        return "{0:.2f} MB".format(B / MB)
    elif GB <= B < TB:
        return "{0:.2f} GB".format(B / GB)
    elif TB <= B:
        return "{0:.2f} TB".format(B / TB)


def format_kbps(bits):
    bits = int(bits)
    return round(bits / 1000)


def hms_format(seconds):
    val = "Unknown"
    if seconds is not None:
        seconds = int(seconds)
        val = time.strftime("%H:%M:%S", time.gmtime(seconds))
    return val


def format_clipLength(seconds):
    if int(seconds) == 301:
        return "Infinite"
    else:
        return hms_format(seconds)


def get_topicName(topicID):
    topicID = int(topicID)
    if topicID in globalvars.topicCache:
        return globalvars.topicCache[topicID]
    return "None"


def get_userName(userID):
    userQuery = cachedDbCalls.getUser(userID)
    if userQuery is None:
        return "Unknown User"
    else:
        return userQuery.username


def get_Video_Upvotes_Filter(videoID):
    result = votes.get_Video_Upvotes(videoID)
    return result


def get_Stream_Upvotes_Filter(videoID):
    result = votes.get_Stream_Upvotes(videoID)
    return result


def get_Clip_Upvotes_Filter(videoID):
    result = votes.get_Clip_Upvotes(videoID)
    return result


def get_Video_Comments_Filter(videoID):
    result = cachedDbCalls.getVideoCommentCount(videoID)
    return result


def get_pictureLocation(userID):
    pictureLocation = cachedDbCalls.getUserPhotoLocation(userID)
    return pictureLocation


def channeltoOwnerID(channelID):
    channelObj = cachedDbCalls.getChannel(channelID)
    return channelObj.owningUser


def get_channelPrivateStatus(channelID):
    channelObj = cachedDbCalls.getChannel(channelID)
    if channelObj is not None:
        if channelObj.private is False:
            return False
        else:
            return True
    return True


def get_channelTopic(channelID):
    channelObj = cachedDbCalls.getChannel(channelID)
    return channelObj.topic


def videotoChannelID(videoID):
    videoObj = cachedDbCalls.getVideo(videoID)
    return videoObj.channelID


def get_videoTopic(videoID):
    videoObj = cachedDbCalls.getVideo(videoID)
    return videoObj.topic


def get_diskUsage(channelLocation):
    videos_root = globalvars.videoRoot + "videos/"
    channelLocation = videos_root + channelLocation

    total_size = 0
    for dirpath, dirnames, filenames in os.walk(channelLocation):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


def testList(obj):
    if type(obj) == list:
        return True
    else:
        return False


def processClientCount(data):
    count = 0
    if type(data) == list:
        for client in data:
            if "flashver" in client:
                if client["flashver"] != "ngx-local-relay":
                    count = count + 1
    else:
        count = 1
    return count


def uuid_to_username(uuid):
    if "@" in uuid:
        JID = uuid.split("@")[0]
    else:
        JID = uuid
    userQuery = Sec.User.query.filter_by(uuid=JID).first()
    if userQuery is not None:
        result = userQuery.username
    else:
        result = None
    return result


def get_webhookTrigger(webhookTrigger):

    webhookTrigger = str(webhookTrigger)
    webhookNames = {
        "0": "Stream Start",
        "1": "Stream End",
        "2": "Stream Viewer Join",
        "3": "Stream Viewer Upvote",
        "4": "Stream Name Change",
        "5": "Chat Message",
        "6": "New Video",
        "7": "Video Comment",
        "8": "Video Upvote",
        "9": "Video Name Change",
        "10": "Channel Subscription",
        "20": "New User",
    }
    return webhookNames[webhookTrigger]


def get_logType(logType):

    logType = str(logType)
    logTypeNames = {
        "0": "System",
        "1": "Security",
        "2": "Email",
        "3": "Channel",
        "4": "Video",
        "5": "Stream",
        "6": "Clip",
        "7": "API",
        "8": "Webhook",
        "9": "Topic",
        "10": "Hub",
    }
    return logTypeNames[logType]


def format_keyType(keyType):
    keyType = str(keyType)
    keyTypeNames = {"1": "User", "2": "Admin"}
    return keyTypeNames[keyType]


def get_channelSubCount(channelID):
    subCount = cachedDbCalls.getChannelSubCount(channelID)
    return subCount


def get_channelLiveStatus(channelID):
    isChannelLive = cachedDbCalls.isChannelLive(channelID)
    return isChannelLive


def get_channelName(channelID):
    channelQuery = cachedDbCalls.getChannel(channelID)
    return channelQuery.channelName


def get_channelProtected(channelID):
    sysSettings = cachedDbCalls.getSystemSettings()
    channelQuery = cachedDbCalls.getChannel(channelID)
    protected = False
    if channelQuery != None:
        if channelQuery.protected is True and sysSettings.protectionEnabled is True:
            protected = True
    return protected


def get_channelLocationFromID(channelID):
    channelQuery = cachedDbCalls.getChannelLocationFromID(channelID)
    return channelQuery


def get_videoDate(videoID):
    videoQuery = cachedDbCalls.getVideo(videoID)
    return videoQuery.videoDate


def get_videoComments(videoID):
    commentsQuery = comments.videoComments.query.filter_by(videoID=videoID).all()
    return commentsQuery


def get_clipTags(clipId):
    tagQuery = RecordedVideo.clip_tags.query.filter_by(clipID=clipId).all()
    return tagQuery


def get_clipTags_csv(clipId):
    tagQuery = RecordedVideo.clip_tags.query.filter_by(clipID=clipId).all()
    tagArray = []
    for tag in tagQuery:
        tagArray.append(tag.name)
    tagString = ",".join(tagArray)
    return tagString


def get_videoTags(videoId):
    tagQuery = RecordedVideo.video_tags.query.filter_by(videoID=videoId).all()
    return tagQuery


def get_videoTags_csv(videoId):
    tagQuery = RecordedVideo.video_tags.query.filter_by(videoID=videoId).all()
    tagArray = []
    for tag in tagQuery:
        tagArray.append(tag.name)
    tagString = ",".join(tagArray)
    return tagString


def get_channelTags(channelId):
    tagQuery = Channel.channel_tags.query.filter_by(channelID=channelId).all()
    return tagQuery


def get_channelTags_csv(channelId):
    tagQuery = Channel.channel_tags.query.filter_by(channelID=channelId).all()
    tagArray = []
    for tag in tagQuery:
        tagArray.append(tag.name)
    tagString = ",".join(tagArray)
    return tagString


def get_channelPicture(channelID):
    channelQuery = cachedDbCalls.getChannel(channelID)
    return channelQuery.imageLocation


def is_channelObjVisible(channelID):
    channelQuery = cachedDbCalls.getChannel(channelID)
    visible = False
    if channelQuery != None:
        if channelQuery.private:
            if current_user.is_authenticated:
                if current_user.id == channelQuery.owningUser or current_user.has_role(
                    "Admin"
                ):
                    visible = True
        else:
            visible = True
    return visible


def localize_time(timeObj):
    sysSettings = cachedDbCalls.getSystemSettings()
    localtz = pytz.timezone(sysSettings.serverTimeZone)
    localized_datetime = localtz.localize(timeObj)
    return localized_datetime


def epoch_to_datetime(timestamp):
    if timestamp is None:
        return "N/A"
    return datetime.datetime.fromtimestamp(timestamp)


def convert_mins(timestamp):
    if timestamp is not None:
        minutes = round(timestamp / 60)
        return minutes
    else:
        return "?"


def globalPanelIdToPanelName(panelId):

    panelQuery = cachedDbCalls.getGlobalPanel(panelId)
    if panelQuery is not None:
        return panelQuery.name
    else:
        return "Unknown Panel ID # " + panelId


def channelPanelIdToPanelName(panelId):

    panelQuery = cachedDbCalls.getChannelPanel(panelId)
    if panelQuery is not None:
        return panelQuery.name
    else:
        return "Unknown Panel ID # " + panelId


def panelTypeIdToPanelTypeName(panelType):
    panelTypeMap = {
        0: "Text/Markdown",
        1: "Live Stream List",
        2: "Video List",
        3: "Clip List",
        4: "Topic List",
        5: "Channel List",
        6: "Featured Live Stream",
    }
    return panelTypeMap[panelType]


def panelOrderIdToPanelOrderName(panelOrder):
    panelOrderMap = {0: "Most Views / Live Viewers", 1: "Most Recent", 2: "Random"}
    return panelOrderMap[panelOrder]


def getPanel(panelId, panelType):
    panel = None
    if panelType == 0:
        panel = cachedDbCalls.getGlobalPanel(panelId)
    elif panelType == 2:
        panel = cachedDbCalls.getChannelPanel(panelId)
    return panel


def getChannelPanels(channelId):
    panelQuery = panel.channelPanel.query.filter_by(channelId=channelId).all()
    return panelQuery


def getLiveStream(channelId):
    liveStreamQuery = (
        Stream.Stream.query.filter_by(linkedChannel=channelId, active=True)
        .with_entities(
            Stream.Stream.streamName,
            Stream.Stream.linkedChannel,
            Stream.Stream.currentViewers,
            Stream.Stream.topic,
            Stream.Stream.id,
            Stream.Stream.uuid,
            Stream.Stream.startTimestamp,
            Stream.Stream.totalViewers,
            Stream.Stream.active,
        )
        .first()
    )
    return liveStreamQuery


def getLiveStreamURL(channel):
    sysSettings = cachedDbCalls.getSystemSettings()

    # Stream URL Generation
    streamURL = ""
    edgeQuery = settings.edgeStreamer.query.filter_by(active=True).all()
    if sysSettings.proxyFQDN != None:
        if sysSettings.adaptiveStreaming is True:
            streamURL = "/proxy-adapt/" + channel.channelLoc + ".m3u8"
        else:
            streamURL = "/proxy/" + channel.channelLoc + "/index.m3u8"
    elif edgeQuery != []:
        # Handle Selecting the Node using Round Robin Logic
        if sysSettings.adaptiveStreaming is True:
            streamURL = "/edge-adapt/" + channel.channelLoc + ".m3u8"
        else:
            streamURL = "/edge/" + channel.channelLoc + "/index.m3u8"
    else:
        if sysSettings.adaptiveStreaming is True:
            streamURL = "/live-adapt/" + channel.channelLoc + ".m3u8"
        else:
            streamURL = "/live/" + channel.channelLoc + "/index.m3u8"
    return streamURL


def getGlobalPanelArg(panelId, arg):
    panel = cachedDbCalls.getGlobalPanel(panelId)
    result = getattr(panel, arg)
    return result


def getChannelPanelArg(panelId, arg):
    panel = cachedDbCalls.getChannelPanel(panelId)
    result = getattr(panel, arg)
    return result


def getPanelStreamList(order, limitTo):
    if order == 0:
        activeStreams = (
            Stream.Stream.query.filter_by(active=True)
            .with_entities(
                Stream.Stream.streamName,
                Stream.Stream.linkedChannel,
                Stream.Stream.currentViewers,
                Stream.Stream.topic,
                Stream.Stream.id,
                Stream.Stream.uuid,
                Stream.Stream.startTimestamp,
                Stream.Stream.totalViewers,
                Stream.Stream.active,
            )
            .order_by(Stream.Stream.currentViewers.desc())
            .limit(limitTo)
            .all()
        )
    elif order == 1:
        activeStreams = (
            Stream.Stream.query.filter_by(active=True)
            .with_entities(
                Stream.Stream.streamName,
                Stream.Stream.linkedChannel,
                Stream.Stream.currentViewers,
                Stream.Stream.topic,
                Stream.Stream.id,
                Stream.Stream.uuid,
                Stream.Stream.startTimestamp,
                Stream.Stream.totalViewers,
                Stream.Stream.active,
            )
            .order_by(Stream.Stream.startTimestamp.desc())
            .limit(limitTo)
            .all()
        )
    elif order == 2:
        activeStreams = (
            Stream.Stream.query.filter_by(active=True)
            .with_entities(
                Stream.Stream.streamName,
                Stream.Stream.linkedChannel,
                Stream.Stream.currentViewers,
                Stream.Stream.topic,
                Stream.Stream.id,
                Stream.Stream.uuid,
                Stream.Stream.startTimestamp,
                Stream.Stream.totalViewers,
                Stream.Stream.active,
            )
            .order_by(func.random())
            .limit(limitTo)
            .all()
        )
    else:
        activeStreams = (
            Stream.Stream.query.filter_by(active=True)
            .with_entities(
                Stream.Stream.streamName,
                Stream.Stream.linkedChannel,
                Stream.Stream.currentViewers,
                Stream.Stream.topic,
                Stream.Stream.id,
                Stream.Stream.uuid,
                Stream.Stream.startTimestamp,
                Stream.Stream.totalViewers,
                Stream.Stream.active,
            )
            .order_by(Stream.Stream.currentViewers.desc())
            .limit(limitTo)
            .all()
        )
    return activeStreams


def getPanelVideoList(order, limitTo):
    if order == 0:
        recordedQuery = (
            RecordedVideo.RecordedVideo.query.filter_by(pending=False, published=True)
            .join(
                Channel.Channel,
                RecordedVideo.RecordedVideo.channelID == Channel.Channel.id,
            )
            .join(Sec.User, RecordedVideo.RecordedVideo.owningUser == Sec.User.id)
            .with_entities(
                RecordedVideo.RecordedVideo.id,
                RecordedVideo.RecordedVideo.channelID,
                RecordedVideo.RecordedVideo.owningUser,
                RecordedVideo.RecordedVideo.views,
                RecordedVideo.RecordedVideo.length,
                RecordedVideo.RecordedVideo.thumbnailLocation,
                RecordedVideo.RecordedVideo.channelName,
                RecordedVideo.RecordedVideo.topic,
                RecordedVideo.RecordedVideo.videoDate,
                Sec.User.pictureLocation,
                Channel.Channel.protected,
                Channel.Channel.channelName.label("ChanName"),
            )
            .order_by(RecordedVideo.RecordedVideo.views.desc())
            .limit(limitTo)
            .all()
        )
    elif order == 1:
        recordedQuery = (
            RecordedVideo.RecordedVideo.query.filter_by(pending=False, published=True)
            .join(
                Channel.Channel,
                RecordedVideo.RecordedVideo.channelID == Channel.Channel.id,
            )
            .join(Sec.User, RecordedVideo.RecordedVideo.owningUser == Sec.User.id)
            .with_entities(
                RecordedVideo.RecordedVideo.id,
                RecordedVideo.RecordedVideo.channelID,
                RecordedVideo.RecordedVideo.owningUser,
                RecordedVideo.RecordedVideo.views,
                RecordedVideo.RecordedVideo.length,
                RecordedVideo.RecordedVideo.thumbnailLocation,
                RecordedVideo.RecordedVideo.channelName,
                RecordedVideo.RecordedVideo.topic,
                RecordedVideo.RecordedVideo.videoDate,
                Sec.User.pictureLocation,
                Channel.Channel.protected,
                Channel.Channel.channelName.label("ChanName"),
            )
            .order_by(RecordedVideo.RecordedVideo.videoDate.desc())
            .limit(limitTo)
            .all()
        )
    elif order == 2:
        recordedQuery = (
            RecordedVideo.RecordedVideo.query.filter_by(pending=False, published=True)
            .join(
                Channel.Channel,
                RecordedVideo.RecordedVideo.channelID == Channel.Channel.id,
            )
            .join(Sec.User, RecordedVideo.RecordedVideo.owningUser == Sec.User.id)
            .with_entities(
                RecordedVideo.RecordedVideo.id,
                RecordedVideo.RecordedVideo.channelID,
                RecordedVideo.RecordedVideo.owningUser,
                RecordedVideo.RecordedVideo.views,
                RecordedVideo.RecordedVideo.length,
                RecordedVideo.RecordedVideo.thumbnailLocation,
                RecordedVideo.RecordedVideo.channelName,
                RecordedVideo.RecordedVideo.topic,
                RecordedVideo.RecordedVideo.videoDate,
                Sec.User.pictureLocation,
                Channel.Channel.protected,
                Channel.Channel.channelName.label("ChanName"),
            )
            .order_by(func.random())
            .limit(limitTo)
            .all()
        )
    else:
        recordedQuery = (
            RecordedVideo.RecordedVideo.query.filter_by(pending=False, published=True)
            .join(
                Channel.Channel,
                RecordedVideo.RecordedVideo.channelID == Channel.Channel.id,
            )
            .join(Sec.User, RecordedVideo.RecordedVideo.owningUser == Sec.User.id)
            .with_entities(
                RecordedVideo.RecordedVideo.id,
                RecordedVideo.RecordedVideo.channelID,
                RecordedVideo.RecordedVideo.owningUser,
                RecordedVideo.RecordedVideo.views,
                RecordedVideo.RecordedVideo.length,
                RecordedVideo.RecordedVideo.thumbnailLocation,
                RecordedVideo.RecordedVideo.channelName,
                RecordedVideo.RecordedVideo.topic,
                RecordedVideo.RecordedVideo.videoDate,
                Sec.User.pictureLocation,
                Channel.Channel.protected,
                Channel.Channel.channelName.label("ChanName"),
            )
            .order_by(RecordedVideo.RecordedVideo.views.desc())
            .limit(limitTo)
            .all()
        )
    return recordedQuery


def getPanelClipList(order, limitTo):
    if order == 0:
        clipQuery = (
            RecordedVideo.Clips.query.filter_by(published=True)
            .join(
                RecordedVideo.RecordedVideo,
                RecordedVideo.Clips.parentVideo == RecordedVideo.RecordedVideo.id,
            )
            .join(
                Channel.Channel,
                Channel.Channel.id == RecordedVideo.RecordedVideo.channelID,
            )
            .join(Sec.User, Sec.User.id == Channel.Channel.owningUser)
            .with_entities(
                RecordedVideo.Clips.id,
                RecordedVideo.Clips.thumbnailLocation,
                Channel.Channel.owningUser,
                RecordedVideo.Clips.views,
                RecordedVideo.Clips.length,
                RecordedVideo.Clips.clipName,
                Channel.Channel.protected,
                Channel.Channel.channelName,
                RecordedVideo.RecordedVideo.topic,
                RecordedVideo.RecordedVideo.videoDate,
                Sec.User.pictureLocation,
                RecordedVideo.Clips.parentVideo,
            )
            .order_by(RecordedVideo.Clips.views.desc())
            .limit(limitTo)
            .all()
        )
    elif order == 1:
        clipQuery = (
            RecordedVideo.Clips.query.filter_by(published=True)
            .join(
                RecordedVideo.RecordedVideo,
                RecordedVideo.Clips.parentVideo == RecordedVideo.RecordedVideo.id,
            )
            .join(
                Channel.Channel,
                Channel.Channel.id == RecordedVideo.RecordedVideo.channelID,
            )
            .join(Sec.User, Sec.User.id == Channel.Channel.owningUser)
            .with_entities(
                RecordedVideo.Clips.id,
                RecordedVideo.Clips.thumbnailLocation,
                Channel.Channel.owningUser,
                RecordedVideo.Clips.views,
                RecordedVideo.Clips.length,
                RecordedVideo.Clips.clipName,
                Channel.Channel.protected,
                Channel.Channel.channelName,
                RecordedVideo.RecordedVideo.topic,
                RecordedVideo.RecordedVideo.videoDate,
                Sec.User.pictureLocation,
                RecordedVideo.Clips.parentVideo,
            )
            .order_by(RecordedVideo.RecordedVideo.videoDate.desc())
            .limit(limitTo)
            .all()
        )
    elif order == 2:
        clipQuery = (
            RecordedVideo.Clips.query.filter_by(published=True)
            .join(
                RecordedVideo.RecordedVideo,
                RecordedVideo.Clips.parentVideo == RecordedVideo.RecordedVideo.id,
            )
            .join(
                Channel.Channel,
                Channel.Channel.id == RecordedVideo.RecordedVideo.channelID,
            )
            .join(Sec.User, Sec.User.id == Channel.Channel.owningUser)
            .with_entities(
                RecordedVideo.Clips.id,
                RecordedVideo.Clips.thumbnailLocation,
                Channel.Channel.owningUser,
                RecordedVideo.Clips.views,
                RecordedVideo.Clips.length,
                RecordedVideo.Clips.clipName,
                Channel.Channel.protected,
                Channel.Channel.channelName,
                RecordedVideo.RecordedVideo.topic,
                RecordedVideo.RecordedVideo.videoDate,
                Sec.User.pictureLocation,
                RecordedVideo.Clips.parentVideo,
            )
            .order_by(func.random())
            .limit(limitTo)
            .all()
        )
    else:
        clipQuery = (
            RecordedVideo.Clips.query.filter_by(published=True)
            .join(
                RecordedVideo.RecordedVideo,
                RecordedVideo.Clips.parentVideo == RecordedVideo.RecordedVideo.id,
            )
            .join(
                Channel.Channel,
                Channel.Channel.id == RecordedVideo.RecordedVideo.channelID,
            )
            .join(Sec.User, Sec.User.id == Channel.Channel.owningUser)
            .with_entities(
                RecordedVideo.Clips.id,
                RecordedVideo.Clips.thumbnailLocation,
                Channel.Channel.owningUser,
                RecordedVideo.Clips.views,
                RecordedVideo.Clips.length,
                RecordedVideo.Clips.clipName,
                Channel.Channel.protected,
                Channel.Channel.channelName,
                RecordedVideo.RecordedVideo.topic,
                RecordedVideo.RecordedVideo.videoDate,
                Sec.User.pictureLocation,
                RecordedVideo.Clips.parentVideo,
            )
            .order_by(RecordedVideo.Clips.views.desc())
            .limit(limitTo)
            .all()
        )
    return clipQuery


def getPanelChannelList(order, limitTo):
    if order == 0:
        channelQuery = (
            Channel.Channel.query.with_entities(
                Channel.Channel.id,
                Channel.Channel.owningUser,
                Channel.Channel.channelName,
                Channel.Channel.channelLoc,
                Channel.Channel.topic,
                Channel.Channel.views,
                Channel.Channel.currentViewers,
                Channel.Channel.record,
                Channel.Channel.chatEnabled,
                Channel.Channel.chatBG,
                Channel.Channel.chatTextColor,
                Channel.Channel.chatAnimation,
                Channel.Channel.imageLocation,
                Channel.Channel.offlineImageLocation,
                Channel.Channel.description,
                Channel.Channel.allowComments,
                Channel.Channel.protected,
                Channel.Channel.channelMuted,
                Channel.Channel.showChatJoinLeaveNotification,
                Channel.Channel.defaultStreamName,
                Channel.Channel.autoPublish,
                Channel.Channel.vanityURL,
                Channel.Channel.private,
                Channel.Channel.streamKey,
                Channel.Channel.xmppToken,
            )
            .order_by(Channel.Channel.views.desc())
            .limit(limitTo)
            .all()
        )
    elif order == 1:
        channelQuery = (
            Channel.Channel.query.with_entities(
                Channel.Channel.id,
                Channel.Channel.owningUser,
                Channel.Channel.channelName,
                Channel.Channel.channelLoc,
                Channel.Channel.topic,
                Channel.Channel.views,
                Channel.Channel.currentViewers,
                Channel.Channel.record,
                Channel.Channel.chatEnabled,
                Channel.Channel.chatBG,
                Channel.Channel.chatTextColor,
                Channel.Channel.chatAnimation,
                Channel.Channel.imageLocation,
                Channel.Channel.offlineImageLocation,
                Channel.Channel.description,
                Channel.Channel.allowComments,
                Channel.Channel.protected,
                Channel.Channel.channelMuted,
                Channel.Channel.showChatJoinLeaveNotification,
                Channel.Channel.defaultStreamName,
                Channel.Channel.autoPublish,
                Channel.Channel.vanityURL,
                Channel.Channel.private,
                Channel.Channel.streamKey,
                Channel.Channel.xmppToken,
            )
            .order_by(Channel.Channel.views.desc())
            .limit(limitTo)
            .all()
        )
    elif order == 2:
        channelQuery = (
            Channel.Channel.query.with_entities(
                Channel.Channel.id,
                Channel.Channel.owningUser,
                Channel.Channel.channelName,
                Channel.Channel.channelLoc,
                Channel.Channel.topic,
                Channel.Channel.views,
                Channel.Channel.currentViewers,
                Channel.Channel.record,
                Channel.Channel.chatEnabled,
                Channel.Channel.chatBG,
                Channel.Channel.chatTextColor,
                Channel.Channel.chatAnimation,
                Channel.Channel.imageLocation,
                Channel.Channel.offlineImageLocation,
                Channel.Channel.description,
                Channel.Channel.allowComments,
                Channel.Channel.protected,
                Channel.Channel.channelMuted,
                Channel.Channel.showChatJoinLeaveNotification,
                Channel.Channel.defaultStreamName,
                Channel.Channel.autoPublish,
                Channel.Channel.vanityURL,
                Channel.Channel.private,
                Channel.Channel.streamKey,
                Channel.Channel.xmppToken,
            )
            .order_by(func.random())
            .limit(limitTo)
            .all()
        )
    else:
        channelQuery = (
            Channel.Channel.query.with_entities(
                Channel.Channel.id,
                Channel.Channel.owningUser,
                Channel.Channel.channelName,
                Channel.Channel.channelLoc,
                Channel.Channel.topic,
                Channel.Channel.views,
                Channel.Channel.currentViewers,
                Channel.Channel.record,
                Channel.Channel.chatEnabled,
                Channel.Channel.chatBG,
                Channel.Channel.chatTextColor,
                Channel.Channel.chatAnimation,
                Channel.Channel.imageLocation,
                Channel.Channel.offlineImageLocation,
                Channel.Channel.description,
                Channel.Channel.allowComments,
                Channel.Channel.protected,
                Channel.Channel.channelMuted,
                Channel.Channel.showChatJoinLeaveNotification,
                Channel.Channel.defaultStreamName,
                Channel.Channel.autoPublish,
                Channel.Channel.vanityURL,
                Channel.Channel.private,
                Channel.Channel.streamKey,
                Channel.Channel.xmppToken,
            )
            .order_by(Channel.Channel.views.desc())
            .limit(limitTo)
            .all()
        )
    return channelQuery


def orderVideoBy(videoList, orderById):
    # Most Views
    if orderById == 0:
        return sorted(videoList, key=lambda x: x.views, reverse=True)
    # Most Recent
    elif orderById == 1:
        return sorted(videoList, key=lambda x: x.videoDate, reverse=True)
    # Random
    elif orderById == 2:
        itemList = []
        for item in videoList:
            itemList.append(item)
        random.shuffle(itemList)
        return itemList
    # Fallback Most Views
    else:
        return sorted(videoList, key=lambda x: x.views, reverse=True)


def generatePlaybackAuthToken(channelLoc):
    validationToken = "NA"
    if current_user.is_authenticated:
        if current_user.authType == 0:
            validationToken = hashlib.sha256(
                (current_user.username + channelLoc + current_user.password).encode(
                    "utf-8"
                )
            ).hexdigest()
        else:
            validationToken = hashlib.sha256(
                (current_user.username + channelLoc + current_user.oAuthID).encode(
                    "utf-8"
                )
            ).hexdigest()
    return validationToken


def get_channelInviteCodes(channelID):
    codeQuery = invites.inviteCode.query.filter_by(channelID=channelID).all()
    return codeQuery


def get_channelInvitedUsers(channelID):
    inviteQuery = invites.invitedViewer.query.filter_by(channelID=channelID).all()
    return inviteQuery


def get_channelRestreamDestinations(channelID):
    restreamDestQuery = Channel.restreamDestinations.query.filter_by(
        channel=channelID
    ).all()
    return restreamDestQuery


def get_channelWebhooks(channelID):
    webhookQuery = webhook.webhook.query.filter_by(channelID=channelID).all()
    return webhookQuery


def get_channelVideos(channelID):
    videosQuery = cachedDbCalls.getChannelVideos(channelID)
    return videosQuery


def get_channelClips(channelID):
    channelVideos = get_channelVideos(channelID)

    videoIDList = []
    for video in channelVideos:
        if video.id not in videoIDList:
            videoIDList.append(video.id)

    clipQuery = (
        RecordedVideo.Clips.query.filter(
            RecordedVideo.Clips.parentVideo.in_(videoIDList)
        )
        .with_entities(
            RecordedVideo.Clips.id,
            RecordedVideo.Clips.gifLocation,
            RecordedVideo.Clips.thumbnailLocation,
            RecordedVideo.Clips.clipName,
            RecordedVideo.Clips.videoLocation,
            RecordedVideo.Clips.length,
            RecordedVideo.Clips.views,
            RecordedVideo.Clips.description,
            RecordedVideo.Clips.published,
            RecordedVideo.Clips.parentVideo,
        )
        .all()
    )
    return clipQuery


def get_flaggedForDeletion(userID):
    flagQuery = Sec.UsersFlaggedForDeletion.query.filter_by(userID=int(userID)).first()
    if flagQuery != None:
        return str(flagQuery.timestamp)
    else:
        return ""


def get_channelData(channelID):
    channelQuery = cachedDbCalls.getChannel(int(channelID))
    return channelQuery


def get_channelStickers(channelID):
    stickerQuery = (
        stickers.stickers.query.filter_by(channelID=channelID)
        .with_entities(
            stickers.stickers.id,
            stickers.stickers.filename,
            stickers.stickers.name,
            stickers.stickers.channelID,
        )
        .all()
    )
    return stickerQuery
