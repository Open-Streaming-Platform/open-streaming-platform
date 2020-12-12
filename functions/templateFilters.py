from urllib.parse import urlparse
import time
import os
import json

from globals import globalvars

from classes import Sec
from classes import topics

from functions import votes
from functions import commentsFunc

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
    userQuery = Sec.User.query.filter_by(id=int(userID)).first()
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
    result = commentsFunc.get_Video_Comments(videoID)
    return result

def get_pictureLocation(userID):
    userQuery = Sec.User.query.filter_by(id=int(userID)).first()
    pictureLocation = None
    if userQuery.pictureLocation is None:
        pictureLocation = '/static/img/user2.png'
    else:
        pictureLocation = '/images/' + userQuery.pictureLocation

    return pictureLocation

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