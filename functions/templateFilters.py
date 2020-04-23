from urllib.parse import urlparse
import time
import os

from flask import current_app

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
    context.jinja_env.filters['get_hubStatus'] = get_hubStatus
    context.jinja_env.filters['get_logType'] = get_logType


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

def format_kbps(bits):
    bits = int(bits)
    return round(bits/1000)

def hms_format(seconds):
    val = "Unknown"
    if seconds is not None:
        seconds = int(seconds)
        val = time.strftime("%H:%M:%S", time.gmtime(seconds))
    return val

def get_topicName(topicID):
    topicQuery = topics.topics.query.filter_by(id=int(topicID)).first()
    if topicQuery is None:
        return "None"
    return topicQuery.name

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
    with current_app.app_context:
        videos_root = current_app.config['WEB_ROOT'] + 'videos/'
        channelLocation = videos_root + channelLocation

        total_size = 0
        for dirpath, dirnames, filenames in os.walk(channelLocation):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return "{:,}".format(total_size)

def testList(obj):
    if type(obj) == list:
        return True
    else:
        return False

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

def get_hubStatus(hubStatus):

    hubStatus = str(hubStatus)
    hubStatusNames = {
        '0': 'Unverified',
        '1': 'Verified'
    }
    return hubStatusNames[hubStatus]

#@app.template_filter('get_hubName')
#def get_hubName(hubID):
#
#    hubID = int(hubID)
#    hubQuery = hubConnection.hubServers.query.filter_by(id=hubID).first()
#    if hubQuery != None:
#        return hubQuery.serverAddress
#    return "Unknown"

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