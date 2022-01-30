from classes.shared import db

from classes import settings
from classes import Channel
from classes import RecordedVideo
from classes import Stream
from classes import subscriptions
from classes import Sec
from classes import topics
from classes import comments
from classes import panel


from classes.shared import cache

### System Settings Related DB Calls
@cache.memoize(timeout=600)
def getSystemSettings():
    sysSettings = settings.settings.query.first()
    return sysSettings

@cache.memoize(timeout=1200)
def getOAuthProviders():
    SystemOAuthProviders = settings.oAuthProvider.query.all()
    return SystemOAuthProviders

### Stream Related DB Calls
@cache.memoize(timeout=60)
def searchStreams(term):
    if term is not None:
        StreamNameQuery = Stream.Stream.query.filter(Stream.Stream.active == True, Stream.Stream.streamName.like("%" + term + "%"))\
            .join(Channel.Channel, Channel.Channel.id == Stream.Stream.linkedChannel)\
            .with_entities(Stream.Stream.id, Stream.Stream.streamName, Channel.Channel.channelLoc, Stream.Stream.uuid, Stream.Stream.linkedChannel,
                           Stream.Stream.topic, Stream.Stream.currentViewers, Stream.Stream.totalViewers, Stream.Stream.active, Stream.Stream.rtmpServer).all()

        resultsArray = StreamNameQuery
        resultsArray = list(set(resultsArray))
        return resultsArray
    else:
        return []

### Channel Related DB Calls
@cache.memoize(timeout=60)
def getAllChannels():
    channelQuery = Channel.Channel.query.\
        with_entities(Channel.Channel.id, Channel.Channel.owningUser, Channel.Channel.channelName, Channel.Channel.channelLoc,
                      Channel.Channel.topic, Channel.Channel.views, Channel.Channel.currentViewers, Channel.Channel.record,
                      Channel.Channel.chatEnabled, Channel.Channel.chatBG, Channel.Channel.chatTextColor, Channel.Channel.chatAnimation,
                      Channel.Channel.imageLocation, Channel.Channel.offlineImageLocation, Channel.Channel.description, Channel.Channel.allowComments,
                      Channel.Channel.protected, Channel.Channel.channelMuted, Channel.Channel.showChatJoinLeaveNotification, Channel.Channel.defaultStreamName,
                      Channel.Channel.autoPublish, Channel.Channel.vanityURL, Channel.Channel.private).all()
    return channelQuery

@cache.memoize(timeout=60)
def getChannel(channelID):
    channelQuery = Channel.Channel.query.\
        with_entities(Channel.Channel.id, Channel.Channel.owningUser, Channel.Channel.channelName, Channel.Channel.channelLoc,
                      Channel.Channel.topic, Channel.Channel.views, Channel.Channel.currentViewers, Channel.Channel.record,
                      Channel.Channel.chatEnabled, Channel.Channel.chatBG, Channel.Channel.chatTextColor, Channel.Channel.chatAnimation,
                      Channel.Channel.imageLocation, Channel.Channel.offlineImageLocation, Channel.Channel.description, Channel.Channel.allowComments,
                      Channel.Channel.protected, Channel.Channel.channelMuted, Channel.Channel.showChatJoinLeaveNotification, Channel.Channel.defaultStreamName,
                      Channel.Channel.autoPublish, Channel.Channel.vanityURL, Channel.Channel.private, Channel.Channel.streamKey, Channel.Channel.xmppToken).filter_by(id=channelID).first()
    return channelQuery

@cache.memoize(timeout=600)
def getChannelByLoc(channelLoc):
    channelQuery = Channel.Channel.query.\
        with_entities(Channel.Channel.id, Channel.Channel.owningUser, Channel.Channel.channelName, Channel.Channel.channelLoc,
                      Channel.Channel.topic, Channel.Channel.views, Channel.Channel.currentViewers, Channel.Channel.record,
                      Channel.Channel.chatEnabled, Channel.Channel.chatBG, Channel.Channel.chatTextColor, Channel.Channel.chatAnimation,
                      Channel.Channel.imageLocation, Channel.Channel.offlineImageLocation, Channel.Channel.description, Channel.Channel.allowComments,
                      Channel.Channel.protected, Channel.Channel.channelMuted, Channel.Channel.showChatJoinLeaveNotification, Channel.Channel.defaultStreamName,
                      Channel.Channel.autoPublish, Channel.Channel.vanityURL, Channel.Channel.private, Channel.Channel.streamKey, Channel.Channel.xmppToken).filter_by(channelLoc=channelLoc).first()
    return channelQuery

@cache.memoize(timeout=600)
def getChannelByStreamKey(StreamKey):
    channelQuery = Channel.Channel.query.\
        with_entities(Channel.Channel.id, Channel.Channel.owningUser, Channel.Channel.channelName, Channel.Channel.channelLoc,
                      Channel.Channel.topic, Channel.Channel.views, Channel.Channel.currentViewers, Channel.Channel.record,
                      Channel.Channel.chatEnabled, Channel.Channel.chatBG, Channel.Channel.chatTextColor, Channel.Channel.chatAnimation,
                      Channel.Channel.imageLocation, Channel.Channel.offlineImageLocation, Channel.Channel.description, Channel.Channel.allowComments,
                      Channel.Channel.protected, Channel.Channel.channelMuted, Channel.Channel.showChatJoinLeaveNotification, Channel.Channel.defaultStreamName,
                      Channel.Channel.autoPublish, Channel.Channel.vanityURL, Channel.Channel.private, Channel.Channel.streamKey, Channel.Channel.xmppToken).filter_by(streamKey=StreamKey).first()
    return channelQuery

@cache.memoize(timeout=60)
def getChannelSubCount(channelID):
    SubscriptionQuery = subscriptions.channelSubs.query.filter_by(channelID=channelID).count()
    return SubscriptionQuery

@cache.memoize(timeout=5)
def isChannelLive(channelID):
    StreamQuery = Stream.Stream.query.filter_by(active=True, linkedChannel=channelID).first()
    if StreamQuery is not None:
        return True
    else:
        return False

@cache.memoize(timeout=10)
def getChannelVideos(channelID):
    VideoQuery = RecordedVideo.RecordedVideo.query.filter_by(channelID=channelID).all()
    return VideoQuery

@cache.memoize(timeout=1200)
def getChannelLocationFromID(channelID):
    ChannelQuery = Channel.Channel.query.filter_by(id=channelID).with_entities(Channel.Channel.id, Channel.Channel.channelLoc).first()
    if ChannelQuery is not None:
        return ChannelQuery.channelLoc
    else:
        return None

@cache.memoize(timeout=1200)
def getChannelIDFromLocation(channelLocation):
    ChannelQuery = Channel.Channel.query.filter_by(channelLoc=channelLocation).with_entities(Channel.Channel.id, Channel.Channel.channelLoc).first()
    if ChannelQuery is not None:
        return ChannelQuery.id
    else:
        return None

@cache.memoize(timeout=120)
def searchChannels(term):
    if term is not None:
        ChannelNameQuery = Channel.Channel.query.filter(Channel.Channel.channelName.like("%" + term + "%"))\
            .with_entities(Channel.Channel.id, Channel.Channel.channelName, Channel.Channel.channelLoc, Channel.Channel.private, Channel.Channel.imageLocation,
                           Channel.Channel.owningUser, Channel.Channel.topic, Channel.Channel.views, Channel.Channel.currentViewers, Channel.Channel.record,
                           Channel.Channel.chatEnabled, Channel.Channel.chatBG, Channel.Channel.chatTextColor, Channel.Channel.chatAnimation,
                           Channel.Channel.offlineImageLocation, Channel.Channel.description, Channel.Channel.allowComments,
                           Channel.Channel.protected, Channel.Channel.channelMuted, Channel.Channel.showChatJoinLeaveNotification, Channel.Channel.defaultStreamName,
                           Channel.Channel.autoPublish, Channel.Channel.vanityURL).all()
        ChannelDescriptionQuery = Channel.Channel.query.filter(Channel.Channel.description.like("%" + term + "%")) \
            .with_entities(Channel.Channel.id, Channel.Channel.channelName, Channel.Channel.channelLoc, Channel.Channel.private, Channel.Channel.imageLocation,
                           Channel.Channel.owningUser, Channel.Channel.topic, Channel.Channel.views, Channel.Channel.currentViewers, Channel.Channel.record,
                           Channel.Channel.chatEnabled, Channel.Channel.chatBG, Channel.Channel.chatTextColor, Channel.Channel.chatAnimation,
                           Channel.Channel.offlineImageLocation, Channel.Channel.description, Channel.Channel.allowComments,
                           Channel.Channel.protected, Channel.Channel.channelMuted, Channel.Channel.showChatJoinLeaveNotification, Channel.Channel.defaultStreamName,
                           Channel.Channel.autoPublish, Channel.Channel.vanityURL).all()
        ChannelTagQuery = Channel.channel_tags.query.filter(Channel.channel_tags.name.like("%" + term + "%")) \
            .with_entities(Channel.channel_tags.id, Channel.channel_tags.name, Channel.channel_tags.channelID).all()

        ChannelTagEntryQuery = []
        for channel in ChannelTagQuery:
            ChannelTagEntryQuery = Channel.Channel.query.filter_by(id=channel.channelID) \
                .with_entities(Channel.Channel.id, Channel.Channel.channelName, Channel.Channel.channelLoc, Channel.Channel.private, Channel.Channel.imageLocation,
                               Channel.Channel.owningUser, Channel.Channel.topic, Channel.Channel.views, Channel.Channel.currentViewers, Channel.Channel.record,
                               Channel.Channel.chatEnabled, Channel.Channel.chatBG, Channel.Channel.chatTextColor, Channel.Channel.chatAnimation,
                               Channel.Channel.offlineImageLocation, Channel.Channel.description, Channel.Channel.allowComments,
                               Channel.Channel.protected, Channel.Channel.channelMuted, Channel.Channel.showChatJoinLeaveNotification, Channel.Channel.defaultStreamName,
                               Channel.Channel.autoPublish, Channel.Channel.vanityURL).all()

        resultsArray = ChannelNameQuery + ChannelDescriptionQuery
        resultsArray = list(set(resultsArray))
        for entry in ChannelTagEntryQuery:
            if entry not in resultsArray:
                resultsArray.append(entry)

        return resultsArray
    else:
        return []

def invalidateChannelCache(channelId):
    lastCachedKey = getChannel(channelId).streamKey
    channelLoc = getChannelLocationFromID(channelId)

    cache.delete_memoized(getChannel, channelId)
    cache.delete_memoized(getChannelByLoc, channelLoc)
    cache.delete_memoized(getChannelByStreamKey, lastCachedKey)

    return True


### Recorded Video Related DB Calls
@cache.memoize(timeout=60)
def getAllVideo_View(channelID):
    recordedVid = RecordedVideo.RecordedVideo.query.filter_by(channelID=channelID, pending=False, published=True). \
        with_entities(RecordedVideo.RecordedVideo.id, RecordedVideo.RecordedVideo.uuid, RecordedVideo.RecordedVideo.videoDate,
                      RecordedVideo.RecordedVideo.owningUser, RecordedVideo.RecordedVideo.channelName, RecordedVideo.RecordedVideo.channelID,
                      RecordedVideo.RecordedVideo.description, RecordedVideo.RecordedVideo.description, RecordedVideo.RecordedVideo.topic,
                      RecordedVideo.RecordedVideo.views, RecordedVideo.RecordedVideo.length, RecordedVideo.RecordedVideo.videoLocation,
                      RecordedVideo.RecordedVideo.thumbnailLocation, RecordedVideo.RecordedVideo.gifLocation, RecordedVideo.RecordedVideo.pending,
                      RecordedVideo.RecordedVideo.allowComments, RecordedVideo.RecordedVideo.published, RecordedVideo.RecordedVideo.originalStreamID).all()
    return recordedVid

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

@cache.memoize(timeout=60)
def getVideoCommentCount(videoID):
    videoCommentsQuery = comments.videoComments.query.filter_by(videoID=videoID).count()
    result = videoCommentsQuery
    return result

@cache.memoize(timeout=120)
def searchVideos(term):
    if term is not None:

        VideoNameQuery = RecordedVideo.RecordedVideo.query.filter(RecordedVideo.RecordedVideo.channelName.like("%" + term + "%"), RecordedVideo.RecordedVideo.published == True)\
            .with_entities(RecordedVideo.RecordedVideo.id, RecordedVideo.RecordedVideo.channelName, RecordedVideo.RecordedVideo.uuid, RecordedVideo.RecordedVideo.thumbnailLocation,
                           RecordedVideo.RecordedVideo.owningUser,  RecordedVideo.RecordedVideo.channelID,
                           RecordedVideo.RecordedVideo.description, RecordedVideo.RecordedVideo.description, RecordedVideo.RecordedVideo.topic,
                           RecordedVideo.RecordedVideo.views, RecordedVideo.RecordedVideo.length, RecordedVideo.RecordedVideo.videoDate, RecordedVideo.RecordedVideo.videoLocation,
                           RecordedVideo.RecordedVideo.gifLocation, RecordedVideo.RecordedVideo.pending,
                           RecordedVideo.RecordedVideo.allowComments, RecordedVideo.RecordedVideo.published, RecordedVideo.RecordedVideo.originalStreamID).all()

        VideoDescriptionQuery = RecordedVideo.RecordedVideo.query.filter(RecordedVideo.RecordedVideo.channelName.like("%" + term + "%"), RecordedVideo.RecordedVideo.published == True)\
            .with_entities(RecordedVideo.RecordedVideo.id, RecordedVideo.RecordedVideo.channelName, RecordedVideo.RecordedVideo.uuid, RecordedVideo.RecordedVideo.thumbnailLocation,
                           RecordedVideo.RecordedVideo.owningUser,  RecordedVideo.RecordedVideo.channelID,
                           RecordedVideo.RecordedVideo.description, RecordedVideo.RecordedVideo.description, RecordedVideo.RecordedVideo.topic,
                           RecordedVideo.RecordedVideo.views, RecordedVideo.RecordedVideo.length, RecordedVideo.RecordedVideo.videoDate, RecordedVideo.RecordedVideo.videoLocation,
                           RecordedVideo.RecordedVideo.gifLocation, RecordedVideo.RecordedVideo.pending,
                           RecordedVideo.RecordedVideo.allowComments, RecordedVideo.RecordedVideo.published, RecordedVideo.RecordedVideo.originalStreamID).all()

        VideoTagQuery = RecordedVideo.video_tags.query.filter(RecordedVideo.video_tags.name.like("%" + term + "%"))\
            .with_entities(RecordedVideo.video_tags.id, RecordedVideo.video_tags.name, RecordedVideo.video_tags.videoID)

        VideoTagEntryQuery = []
        for vid in VideoTagQuery:
            VideoTagEntryQuery = RecordedVideo.RecordedVideo.query.filter_by(id=vid.videoID, published=True)\
                .with_entities(RecordedVideo.RecordedVideo.id, RecordedVideo.RecordedVideo.channelName, RecordedVideo.RecordedVideo.uuid, RecordedVideo.RecordedVideo.thumbnailLocation,
                           RecordedVideo.RecordedVideo.owningUser,  RecordedVideo.RecordedVideo.channelID,
                           RecordedVideo.RecordedVideo.description, RecordedVideo.RecordedVideo.description, RecordedVideo.RecordedVideo.topic,
                           RecordedVideo.RecordedVideo.views, RecordedVideo.RecordedVideo.length, RecordedVideo.RecordedVideo.videoDate, RecordedVideo.RecordedVideo.videoLocation,
                           RecordedVideo.RecordedVideo.gifLocation, RecordedVideo.RecordedVideo.pending,
                           RecordedVideo.RecordedVideo.allowComments, RecordedVideo.RecordedVideo.published, RecordedVideo.RecordedVideo.originalStreamID).all()

        resultsArray = VideoNameQuery + VideoDescriptionQuery
        resultsArray = list(set(resultsArray))
        for entry in VideoTagEntryQuery:
            if entry not in resultsArray:
                resultsArray.append(entry)

        return resultsArray
    else:
        return []

### Clip Related DB Calls
@cache.memoize(timeout=30)
def getClipChannelID(clipID):
    ClipQuery = RecordedVideo.Clips.query.filter_by(id=clipID).first()
    if ClipQuery is not None:
        RecordedVideoQuery = RecordedVideo.RecordedVideo.query.filter_by(id=ClipQuery.parentVideo).first()
        if RecordedVideo is not None:
            ChannelQuery = Channel.Channel.query.filter_by(id=RecordedVideoQuery.channelID).first()
            if ChannelQuery is not None:
                return ChannelQuery.id
    return None

@cache.memoize(timeout=60)
def getAllClipsForChannel_View(channelID):
    VideoQuery = getChannelVideos(channelID)
    clipList = []
    for vid in VideoQuery:
        clipQuery = RecordedVideo.Clips.query.filter_by(parentVideo=vid.id, published=True).all()
        clipList = clipList + clipQuery
    return clipList

@cache.memoize(timeout=120)
def searchClips(term):
    if term is not None:
        clipNameQuery = RecordedVideo.Clips.query.filter(RecordedVideo.Clips.clipName.like("%" + term + "%"), RecordedVideo.Clips.published == True)\
            .join(RecordedVideo.RecordedVideo, RecordedVideo.Clips.parentVideo == RecordedVideo.RecordedVideo.id) \
            .join(Channel.Channel, Channel.Channel.id == RecordedVideo.RecordedVideo.channelID) \
            .join(Sec.User, Sec.User.id == Channel.Channel.owningUser) \
            .with_entities(RecordedVideo.Clips.id, RecordedVideo.Clips.clipName, RecordedVideo.Clips.uuid, RecordedVideo.Clips.thumbnailLocation,
                           Channel.Channel.owningUser, RecordedVideo.Clips.views, RecordedVideo.Clips.length,
                           Channel.Channel.protected, Channel.Channel.channelName,
                           RecordedVideo.RecordedVideo.topic, Sec.User.pictureLocation, RecordedVideo.Clips.parentVideo).all()

        clipDescriptionQuery = RecordedVideo.Clips.query.filter(RecordedVideo.Clips.clipName.like("%" + term + "%"), RecordedVideo.Clips.published == True)\
            .join(RecordedVideo.RecordedVideo, RecordedVideo.Clips.parentVideo == RecordedVideo.RecordedVideo.id) \
            .join(Channel.Channel, Channel.Channel.id == RecordedVideo.RecordedVideo.channelID) \
            .join(Sec.User, Sec.User.id == Channel.Channel.owningUser) \
            .with_entities(RecordedVideo.Clips.id, RecordedVideo.Clips.clipName, RecordedVideo.Clips.uuid, RecordedVideo.Clips.thumbnailLocation,
                           Channel.Channel.owningUser, RecordedVideo.Clips.views, RecordedVideo.Clips.length,
                           Channel.Channel.protected, Channel.Channel.channelName,
                           RecordedVideo.RecordedVideo.topic, Sec.User.pictureLocation, RecordedVideo.Clips.parentVideo).all()

        resultsArray = clipNameQuery + clipDescriptionQuery
        resultsArray = list(set(resultsArray))
        return resultsArray
    else:
        return []

### Topic Related DB Calls
@cache.memoize(timeout=120)
def getAllTopics():
    topicQuery = topics.topics.query.all()
    return topicQuery

@cache.memoize(timeout=120)
def searchTopics(term):
    if term is not None:
        topicNameQuery = topics.topics.query.filter(topics.topics.name.like("%" + term + "%"))\
            .with_entities(topics.topics.id, topics.topics.name).all()
        resultsArray = topicNameQuery
        resultsArray = list(set(resultsArray))
        return resultsArray
    else:
        return []

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

@cache.memoize(timeout=30)
def getUser(userID):
    UserQuery = Sec.User.query.filter_by(id=userID).first()
    return UserQuery

@cache.memoize(timeout=120)
def searchUsers(term):
    if term is not None:
        userNameQuery = Sec.User.query.filter(Sec.User.username.like("%" + term + "%"), Sec.User.active == True)\
            .with_entities(Sec.User.id, Sec.User.username, Sec.User.uuid, Sec.User.pictureLocation).all()
        userDescriptionQuery = Sec.User.query.filter(Sec.User.biography.like("%" + term + "%"), Sec.User.active == True)\
            .with_entities(Sec.User.id, Sec.User.username, Sec.User.uuid, Sec.User.pictureLocation).all()
        resultsArray = userNameQuery + userDescriptionQuery
        resultsArray = list(set(resultsArray))
        return resultsArray
    else:
        return []

@cache.memoize(timeout=30)
def getGlobalPanel(panelId):
    panelQuery = panel.globalPanel.query.filter_by(id=panelId).first()
    return panelQuery

@cache.memoize(timeout=30)
def getUserPanel(panelId):
    panelQuery = panel.userPanel.query.filter_by(id=panelId).first()
    return panelQuery

@cache.memoize(timeout=30)
def getChannelPanel(panelId):
    panelQuery = panel.channelPanel.query.filter_by(id=panelId).first()
    return panelQuery