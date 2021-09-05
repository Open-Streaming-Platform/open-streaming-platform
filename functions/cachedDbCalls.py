from classes.shared import db

from classes import settings
from classes import Channel
from classes import RecordedVideo
from classes import Stream
from classes import subscriptions
from classes import Sec
from classes import topics

from classes.shared import cache


### Channel Related DB Calls
@cache.memoize(timeout=60)
def getAllChannels():
    channelQuery = Channel.Channel.query.\
        with_entities(Channel.Channel.id, Channel.Channel.owningUser, Channel.Channel.channelName, Channel.Channel.channelLoc,
                      Channel.Channel.topic, Channel.Channel.views, Channel.Channel.currentViewers, Channel.Channel.record,
                      Channel.Channel.chatEnabled, Channel.Channel.chatBG, Channel.Channel.chatTextColor, Channel.Channel.chatAnimation,
                      Channel.Channel.imageLocation, Channel.Channel.offlineImageLocation, Channel.Channel.description, Channel.Channel.allowComments,
                      Channel.Channel.protected, Channel.Channel.channelMuted, Channel.Channel.showChatJoinLeaveNotification, Channel.Channel.defaultStreamName,
                      Channel.Channel.autoPublish, Channel.Channel.vanityURL).all()
    return channelQuery

@cache.memoize(timeout=60)
def getChannel(channelID):
    channelQuery = Channel.Channel.query.\
        with_entities(Channel.Channel.id, Channel.Channel.owningUser, Channel.Channel.channelName, Channel.Channel.channelLoc,
                      Channel.Channel.topic, Channel.Channel.views, Channel.Channel.currentViewers, Channel.Channel.record,
                      Channel.Channel.chatEnabled, Channel.Channel.chatBG, Channel.Channel.chatTextColor, Channel.Channel.chatAnimation,
                      Channel.Channel.imageLocation, Channel.Channel.offlineImageLocation, Channel.Channel.description, Channel.Channel.allowComments,
                      Channel.Channel.protected, Channel.Channel.channelMuted, Channel.Channel.showChatJoinLeaveNotification, Channel.Channel.defaultStreamName,
                      Channel.Channel.autoPublish, Channel.Channel.vanityURL).filter_by(id=channelID).first()
    return channelQuery

@cache.memoize(timeout=60)
def getChannelSubCount(channelID):
    SubscriptionQuery = subscriptions.channelSubs.query.filter_by(channelID=channelID).count()
    return SubscriptionQuery

@cache.memoize(timeout=5)
def isChannelLive(channelID):
    StreamQuery = Stream.Stream.query.filter_by(linkedChannel=channelID).first()
    if StreamQuery is not None:
        return True
    else:
        return False

### Recorded Video Related DB Calls
@cache.memoize(timeout=60)
def getVideo(videoID):
    recordedVid = RecordedVideo.RecordedVideo.query.filter_by(id=videoID). \
        with_entities(RecordedVideo.RecordedVideo.id, RecordedVideo.RecordedVideo.uuid, RecordedVideo.RecordedVideo.videoDate,
                      RecordedVideo.RecordedVideo.owningUser, RecordedVideo.RecordedVideo.channelName, RecordedVideo.RecordedVideo.channelID,
                      RecordedVideo.RecordedVideo.description, RecordedVideo.RecordedVideo.description, RecordedVideo.RecordedVideo.topic,
                      RecordedVideo.RecordedVideo.views, RecordedVideo.RecordedVideo.length, RecordedVideo.RecordedVideo.videoLocation,
                      RecordedVideo.RecordedVideo.thumbnailLocation, RecordedVideo.RecordedVideo.gifLocation, RecordedVideo.RecordedVideo.pending,
                      RecordedVideo.RecordedVideo.allowComments, RecordedVideo.RecordedVideo.published, RecordedVideo.RecordedVideo.originalStreamID).first()
    return recordedVid

### Topic Related DB Calls
@cache.memoize(timeout=120)
def getAllTopics():
    topicQuery = topics.topics.query.all()
    return topicQuery

### User Related DB Calls
@cache.memoize(timeout=300)
def getUserPhotoLocation(userID):
    UserQuery = Sec.User.query.filter_by(id=userID).with_entities(Sec.User.id,Sec.User.pictureLocation).first()
    if UserQuery is not None:
        if UserQuery.pictureLocation is None or UserQuery.pictureLocation == "":
            return "/static/img/user2.png"
        return UserQuery.pictureLocation
    else:
        return "/static/img/user2.png"

