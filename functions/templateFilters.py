from urllib.parse import urlparse
import time
import datetime
import os
import pytz
import random

from globals import globalvars

from classes import Sec
from classes import comments
from classes import panel

from functions import votes
from functions import cachedDbCalls

def init(context):
    context.jinja_env.filters['normalize_uuid'] = normalize_uuid
    context.jinja_env.filters['normalize_urlroot'] = normalize_urlroot
    context.jinja_env.filters['normalize_url'] = normalize_url
    context.jinja_env.filters['normalize_date'] = normalize_date
    context.jinja_env.filters['limit_title'] = limit_title
    context.jinja_env.filters['format_kbps'] = format_kbps
    context.jinja_env.filters['hms_format'] = hms_format
    context.jinja_env.filters['get_topicName'] = get_topicName
    context.jinja_env.filters['get_userName'] = get_userName
    context.jinja_env.filters['get_channelSubCount'] = get_channelSubCount
    context.jinja_env.filters['get_Video_Upvotes'] = get_Video_Upvotes_Filter
    context.jinja_env.filters['get_Stream_Upvotes'] = get_Stream_Upvotes_Filter
    context.jinja_env.filters['get_Clip_Upvotes'] = get_Clip_Upvotes_Filter
    context.jinja_env.filters['get_Video_Comments'] = get_Video_Comments_Filter
    context.jinja_env.filters['get_pictureLocation'] = get_pictureLocation
    context.jinja_env.filters['get_diskUsage'] = get_diskUsage
    context.jinja_env.filters['testList'] = testList
    context.jinja_env.filters['get_webhookTrigger'] = get_webhookTrigger
    context.jinja_env.filters['get_logType'] = get_logType
    context.jinja_env.filters['format_clipLength'] = format_clipLength
    context.jinja_env.filters['processClientCount'] = processClientCount
    context.jinja_env.filters['formatSpace'] = formatSpace
    context.jinja_env.filters['uuid_to_username'] = uuid_to_username
    context.jinja_env.filters['format_keyType'] = format_keyType
    context.jinja_env.filters['get_channelLiveStatus'] = get_channelLiveStatus
    context.jinja_env.filters['get_channelName'] = get_channelName
    context.jinja_env.filters['get_videoComments'] = get_videoComments
    context.jinja_env.filters['get_channelProtected'] = get_channelProtected
    context.jinja_env.filters['get_channelLocationFromID'] = get_channelLocationFromID
    context.jinja_env.filters['channeltoOwnerID'] = channeltoOwnerID
    context.jinja_env.filters['videotoChannelID'] = videotoChannelID
    context.jinja_env.filters['get_channelTopic'] = get_channelTopic
    context.jinja_env.filters['get_videoTopic'] = get_videoTopic
    context.jinja_env.filters['get_videoDate'] = get_videoDate
    context.jinja_env.filters['get_channelPicture'] = get_channelPicture
    context.jinja_env.filters['localize_time'] = localize_time
    context.jinja_env.filters['epoch_to_datetime'] = epoch_to_datetime
    context.jinja_env.filters['convert_mins'] = convert_mins
    context.jinja_env.filters['globalPanelIdToPanelName'] = globalPanelIdToPanelName
    context.jinja_env.filters['channelPanelIdToPanelName'] = channelPanelIdToPanelName
    context.jinja_env.filters['panelOrderIdToPanelOrderName'] = panelOrderIdToPanelOrderName
    context.jinja_env.filters['panelTypeIdToPanelTypeName'] = panelTypeIdToPanelTypeName
    context.jinja_env.filters['getGlobalPanelArg'] = getGlobalPanelArg
    context.jinja_env.filters['getPanel'] = getPanel
    context.jinja_env.filters['orderVideoBy'] = orderVideoBy

#----------------------------------------------------------------------------#
# Template Filters
#----------------------------------------------------------------------------#

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
    reparsedString = str(URLProtocol) + "://" + str(parsedURL.hostname) + str(parsedURL.path)
    return str(reparsedString)

def normalize_date(dateStr):
    return str(dateStr)[:19]

def limit_title(titleStr):
    if len(titleStr) > 40:
        return titleStr[:37] + "..."
    else:
        return titleStr

def formatSpace(B):
    'Return the given bytes as a human friendly KB, MB, GB, or TB string'
    B = float(B)
    KB = float(1024)
    MB = float(KB ** 2)  # 1,048,576
    GB = float(KB ** 3)  # 1,073,741,824
    TB = float(KB ** 4)  # 1,099,511,627,776

    if B < KB:
        return '{0} {1}'.format(B, 'Bytes' if 0 == B > 1 else 'Byte')
    elif KB <= B < MB:
        return '{0:.2f} KB'.format(B / KB)
    elif MB <= B < GB:
        return '{0:.2f} MB'.format(B / MB)
    elif GB <= B < TB:
        return '{0:.2f} GB'.format(B / GB)
    elif TB <= B:
        return '{0:.2f} TB'.format(B / TB)

def format_kbps(bits):
    bits = int(bits)
    return round(bits/1000)

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
        videos_root = globalvars.videoRoot + 'videos/'
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
            if 'flashver' in client:
                if client['flashver'] != 'ngx-local-relay':
                    count = count + 1
    else:
        count = 1
    return count

def uuid_to_username(uuid):
    if '@' in uuid:
        JID=uuid.split('@')[0]
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

def format_keyType(keyType):
    keyType = str(keyType)
    keyTypeNames = {
        '1': 'User',
        '2': 'Admin'
    }
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
    channelQuery = cachedDbCalls.getChannel(channelID)
    return channelQuery.protected

def get_channelLocationFromID(channelID):
    channelQuery = cachedDbCalls.getChannelLocationFromID(channelID)
    return channelQuery

def get_videoDate(videoID):
    videoQuery = cachedDbCalls.getVideo(videoID)
    return videoQuery.videoDate

def get_videoComments(videoID):
    commentsQuery = comments.videoComments.query.filter_by(videoID=videoID).all()
    return commentsQuery

def get_channelPicture(channelID):
    channelQuery = cachedDbCalls.getChannel(channelID)
    return channelQuery.imageLocation

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
    panelTypeMap = {0: "Text/Markdown", 1: "Live Stream List", 2: "Video List", 3: "Clip List", 4: "Topic List", 5: "Channel List" }
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

def getGlobalPanelArg(panelId, arg):
    panel = cachedDbCalls.getGlobalPanel(panelId)
    result = getattr(panel, arg)
    return result

def getChannelPanelArg(panelId, arg):
    panel = cachedDbCalls.getChannelPanel(panelId)
    result = getattr(panel, arg)
    return result


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

