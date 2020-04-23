from urllib.parse import urlparse
import time
import os

from flask import current_app as app

from classes import Sec
from classes import topics

from functions import votes
from functions import commentsFunc

#----------------------------------------------------------------------------#
# Template Filters
#----------------------------------------------------------------------------#

@app.template_filter('normalize_uuid')
def normalize_uuid(uuidstr):
    return uuidstr.replace("-", "")

@app.template_filter('normalize_urlroot')
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

@app.template_filter('normalize_url')
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

@app.template_filter('normalize_date')
def normalize_date(dateStr):
    return str(dateStr)[:19]

@app.template_filter('limit_title')
def limit_title(titleStr):
    if len(titleStr) > 40:
        return titleStr[:37] + "..."
    else:
        return titleStr

@app.template_filter('format_kbps')
def format_kbps(bits):
    bits = int(bits)
    return round(bits/1000)

@app.template_filter('hms_format')
def hms_format(seconds):
    val = "Unknown"
    if seconds is not None:
        seconds = int(seconds)
        val = time.strftime("%H:%M:%S", time.gmtime(seconds))
    return val

@app.template_filter('get_topicName')
def get_topicName(topicID):
    topicQuery = topics.topics.query.filter_by(id=int(topicID)).first()
    if topicQuery is None:
        return "None"
    return topicQuery.name


@app.template_filter('get_userName')
def get_userName(userID):
    userQuery = Sec.User.query.filter_by(id=int(userID)).first()
    if userQuery is None:
        return "Unknown User"
    else:
        return userQuery.username

@app.template_filter('get_Video_Upvotes')
def get_Video_Upvotes_Filter(videoID):
    result = votes.get_Video_Upvotes(videoID)
    return result

@app.template_filter('get_Stream_Upvotes')
def get_Stream_Upvotes_Filter(videoID):
    result = votes.get_Stream_Upvotes(videoID)
    return result

@app.template_filter('get_Clip_Upvotes')
def get_Clip_Upvotes_Filter(videoID):
    result = votes.get_Clip_Upvotes(videoID)
    return result

@app.template_filter('get_Video_Comments')
def get_Video_Comments_Filter(videoID):
    result = commentsFunc.get_Video_Comments(videoID)
    return result

@app.template_filter('get_pictureLocation')
def get_pictureLocation(userID):
    userQuery = Sec.User.query.filter_by(id=int(userID)).first()
    pictureLocation = None
    if userQuery.pictureLocation is None:
        pictureLocation = '/static/img/user2.png'
    else:
        pictureLocation = '/images/' + userQuery.pictureLocation

    return pictureLocation

@app.template_filter('get_diskUsage')
def get_diskUsage(channelLocation):

    videos_root = app.config['WEB_ROOT'] + 'videos/'
    channelLocation = videos_root + channelLocation

    total_size = 0
    for dirpath, dirnames, filenames in os.walk(channelLocation):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return "{:,}".format(total_size)

@ app.template_filter('testList')
def testList(obj):
    if type(obj) == list:
        return True
    else:
        return False

@app.template_filter('get_webhookTrigger')
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

@app.template_filter('get_hubStatus')
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

@app.template_filter('get_logType')
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