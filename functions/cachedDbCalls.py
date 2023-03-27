from sqlalchemy import and_
from sqlalchemy.sql.expression import func
import datetime

from classes import settings
from classes import Channel
from classes import RecordedVideo
from classes import Stream
from classes import subscriptions
from classes import Sec
from classes import topics
from classes import comments
from classes import panel
from classes import upvotes
from classes import views
from classes.shared import db
from classes.shared import Dict2Class
from classes.shared import cache

# System Settings Related DB Calls


@cache.memoize(timeout=600)
def getSystemSettings():
    sysSettings = settings.settings.query.first()
    return sysSettings


@cache.memoize(timeout=1200)
def getOAuthProviders():
    SystemOAuthProviders = settings.oAuthProvider.query.all()
    return SystemOAuthProviders


@cache.memoize(timeout=300)
def getChannelLiveViewsByDate(channelId):
    liveViewCountQuery = (
        db.session.query(
            func.date(views.views.date), func.count(views.views.id)
        )
        .filter(views.views.viewType == 0)
        .filter(views.views.itemID == channelId)
        .filter(
            views.views.date
            > (datetime.datetime.utcnow() - datetime.timedelta(days=30))
        )
        .group_by(func.date(views.views.date))
        .all()
    )
    return liveViewCountQuery

@cache.memoize(timeout=600)
def getVideoViewsByDate(videoId):
    videoViewCountQuery = (
        db.session.query(
            func.date(views.views.date), func.count(views.views.id)
        )
        .filter(views.views.viewType==1)
        .filter(views.views.itemID==videoId)
        .filter(views.views.date > (datetime.datetime.utcnow() - datetime.timedelta(days=30)))
        .group_by(func.date(views.views.date))
        .all()
    )
    return videoViewCountQuery

# Stream Related DB Calls
@cache.memoize(timeout=60)
def searchStreams(term):
    if term is not None:
        StreamNameQuery = (
            Stream.Stream.query.filter(
                Stream.Stream.active == True,
                Stream.Stream.streamName.like("%" + term + "%"),
            )
            .join(Channel.Channel, Channel.Channel.id == Stream.Stream.linkedChannel)
            .with_entities(
                Stream.Stream.id,
                Stream.Stream.streamName,
                Channel.Channel.channelLoc,
                Stream.Stream.uuid,
                Stream.Stream.linkedChannel,
                Stream.Stream.topic,
                Stream.Stream.currentViewers,
                Stream.Stream.totalViewers,
                Stream.Stream.active,
                Stream.Stream.rtmpServer,
            )
            .all()
        )

        resultsArray = StreamNameQuery
        resultsArray = list(set(resultsArray))
        return resultsArray
    else:
        return []


# Channel Related DB Calls
@cache.memoize(timeout=60)
def getAllChannels():
    channelQuery = Channel.Channel.query.with_entities(
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
        Channel.Channel.chatFormat,
        Channel.Channel.chatHistory,
        Channel.Channel.allowGuestNickChange,
        Channel.Channel.showHome,
        Channel.Channel.maxVideoRetention,
        Channel.Channel.hubEnabled,
        Channel.Channel.hubNSFW
    ).all()
    return channelQuery


@cache.memoize(timeout=60)
def getChannel(channelID):
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
            Channel.Channel.chatFormat,
            Channel.Channel.chatHistory,
            Channel.Channel.allowGuestNickChange,
            Channel.Channel.showHome,
            Channel.Channel.maxVideoRetention,
            Channel.Channel.hubEnabled,
            Channel.Channel.hubNSFW
        )
        .filter_by(id=channelID)
        .first()
    )
    return channelQuery


@cache.memoize(timeout=600)
def getChannelByLoc(channelLoc):
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
            Channel.Channel.chatFormat,
            Channel.Channel.chatHistory,
            Channel.Channel.allowGuestNickChange,
            Channel.Channel.showHome,
            Channel.Channel.maxVideoRetention,
            Channel.Channel.hubEnabled,
            Channel.Channel.hubNSFW
        )
        .filter_by(channelLoc=channelLoc)
        .first()
    )
    return channelQuery


@cache.memoize(timeout=600)
def getChannelByStreamKey(StreamKey):
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
            Channel.Channel.chatFormat,
            Channel.Channel.chatHistory,
            Channel.Channel.allowGuestNickChange,
            Channel.Channel.showHome,
            Channel.Channel.maxVideoRetention,
            Channel.Channel.hubEnabled,
            Channel.Channel.hubNSFW
        )
        .filter_by(streamKey=StreamKey)
        .first()
    )
    return channelQuery


@cache.memoize(timeout=600)
def getChannelsByOwnerId(OwnerId):
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
            Channel.Channel.chatFormat,
            Channel.Channel.chatHistory,
            Channel.Channel.allowGuestNickChange,
            Channel.Channel.showHome,
            Channel.Channel.maxVideoRetention,
            Channel.Channel.hubEnabled,
            Channel.Channel.hubNSFW
        )
        .filter_by(owningUser=OwnerId)
        .all()
    )
    return channelQuery


@cache.memoize(timeout=30)
def serializeChannelByLocationID(channelLoc):
    channel = getChannelByLoc(channelLoc)
    return serializeChannel(channel.id)


@cache.memoize(timeout=30)
def serializeChannel(channelID):
    channelData = getChannel(channelID)
    return {
        "id": channelData.id,
        "channelEndpointID": channelData.channelLoc,
        "owningUser": channelData.owningUser,
        "owningUsername": getUser(channelData.owningUser).username,
        "channelName": channelData.channelName,
        "description": channelData.description,
        "channelImage": "/images/" + str(channelData.imageLocation),
        "offlineImageLocation": "/images/" + str(channelData.offlineImageLocation),
        "topic": channelData.topic,
        "views": channelData.views,
        "currentViews": channelData.currentViewers,
        "recordingEnabled": channelData.record,
        "chatEnabled": channelData.chatEnabled,
        "stream": [obj.id for obj in getChannelStreamIds(channelData.id)],
        "recordedVideoIDs": [obj.id for obj in getChannelVideos(channelData.id)],
        "upvotes": getChannelUpvotes(channelData.id),
        "protected": channelData.protected,
        "allowGuestNickChange": channelData.allowGuestNickChange,
        "vanityURL": channelData.vanityURL,
        "showHome": channelData.showHome,
        "maxVideoRetention": channelData.maxVideoRetention,
        "subscriptions": getChannelSubCount(channelID),
        "hubEnabled": channelData.hubEnabled,
        "hubNSFW": channelData.hubNSFW,
        "tags": [obj.id for obj in getChannelTagIds(channelData.id)],
    }


@cache.memoize(timeout=30)
def serializeChannels(hubCheck=False):
    if hubCheck is True:
        ChannelQuery = (
            Channel.Channel.query.filter_by(private=False, hubEnabled=True)
            .with_entities(Channel.Channel.id)
            .all()
        )
    else:
        ChannelQuery = (
            Channel.Channel.query.filter_by(private=False)
            .with_entities(Channel.Channel.id)
            .all()
        )
    returnData = []
    for channel in ChannelQuery:
        returnData.append(serializeChannel(channel.id))
    return returnData

@cache.memoize(timeout=30)
def getLiveChannels(hubCheck=False):
    streamQuery = Stream.Stream.query.filter_by(active=True, complete=False).with_entities(Stream.Stream.id, Stream.Stream.linkedChannel).all()
    liveChannelIds = []
    for stream in streamQuery:
        if stream.linkedChannel not in liveChannelIds:
            liveChannelIds.append(stream.linkedChannel)
    liveChannelReturn = []
    for liveChannelId in liveChannelIds:
        serializedData = serializeChannel(liveChannelId)
        if hubCheck is True:
            if serializedData['hubEnabled'] is True:
                liveChannelReturn.append(serializedData)
        else:
            liveChannelReturn.append(serializeChannel(liveChannelId))
    return liveChannelReturn

@cache.memoize(timeout=60)
def getHubChannels():
    channels = serializeChannels(hubCheck=True)
    return channels


@cache.memoize(timeout=30)
def getChannelSubCount(channelID):
    SubscriptionQuery = subscriptions.channelSubs.query.filter_by(
        channelID=channelID
    ).count()
    return SubscriptionQuery


@cache.memoize(timeout=60)
def getChannelUpvotes(channelID):
    UpvoteQuery = upvotes.channelUpvotes.query.filter_by(channelID=channelID).count()
    return UpvoteQuery


@cache.memoize(timeout=5)
def getChannelStreamIds(channelID):
    StreamQuery = (
        Stream.Stream.query.filter_by(active=True, linkedChannel=channelID)
        .with_entities(Stream.Stream.id)
        .all()
    )
    return StreamQuery


@cache.memoize(timeout=5)
def isChannelLive(channelID):
    StreamQuery = Stream.Stream.query.filter_by(
        active=True, linkedChannel=channelID
    ).first()
    if StreamQuery is not None:
        return True
    else:
        return False


@cache.memoize(timeout=30)
def getChannelTagIds(channelID):
    tagQuery = (
        Channel.channel_tags.query.filter_by(channelID=channelID)
        .with_entities(Channel.channel_tags.id)
        .all()
    )
    return tagQuery


@cache.memoize(timeout=10)
def getChannelVideos(channelID):
    VideoQuery = (
        RecordedVideo.RecordedVideo.query.filter_by(channelID=channelID)
        .with_entities(
            RecordedVideo.RecordedVideo.id,
            RecordedVideo.RecordedVideo.channelName,
            RecordedVideo.RecordedVideo.gifLocation,
            RecordedVideo.RecordedVideo.thumbnailLocation,
            RecordedVideo.RecordedVideo.videoLocation,
            RecordedVideo.RecordedVideo.topic,
            RecordedVideo.RecordedVideo.videoDate,
            RecordedVideo.RecordedVideo.length,
            RecordedVideo.RecordedVideo.description,
            RecordedVideo.RecordedVideo.allowComments,
            RecordedVideo.RecordedVideo.views,
            RecordedVideo.RecordedVideo.published,
            RecordedVideo.RecordedVideo.channelID,
            RecordedVideo.RecordedVideo.owningUser,
        )
        .all()
    )
    return VideoQuery


@cache.memoize(timeout=1200)
def getChannelLocationFromID(channelID):
    ChannelQuery = (
        Channel.Channel.query.filter_by(id=channelID)
        .with_entities(Channel.Channel.id, Channel.Channel.channelLoc)
        .first()
    )
    if ChannelQuery is not None:
        return ChannelQuery.channelLoc
    else:
        return None


@cache.memoize(timeout=1200)
def getChannelIDFromLocation(channelLocation):
    ChannelQuery = (
        Channel.Channel.query.filter_by(channelLoc=channelLocation)
        .with_entities(Channel.Channel.id, Channel.Channel.channelLoc)
        .first()
    )
    if ChannelQuery is not None:
        return ChannelQuery.id
    else:
        return None


@cache.memoize(timeout=120)
def searchChannels(term):
    if term is not None:
        ChannelNameQuery = (
            Channel.Channel.query.filter(
                Channel.Channel.channelName.like("%" + term + "%")
            )
            .with_entities(
                Channel.Channel.id,
                Channel.Channel.channelName,
                Channel.Channel.channelLoc,
                Channel.Channel.private,
                Channel.Channel.imageLocation,
                Channel.Channel.owningUser,
                Channel.Channel.topic,
                Channel.Channel.views,
                Channel.Channel.currentViewers,
                Channel.Channel.record,
                Channel.Channel.chatEnabled,
                Channel.Channel.chatBG,
                Channel.Channel.chatTextColor,
                Channel.Channel.chatAnimation,
                Channel.Channel.offlineImageLocation,
                Channel.Channel.description,
                Channel.Channel.allowComments,
                Channel.Channel.protected,
                Channel.Channel.channelMuted,
                Channel.Channel.showChatJoinLeaveNotification,
                Channel.Channel.defaultStreamName,
                Channel.Channel.autoPublish,
                Channel.Channel.vanityURL,
            )
            .all()
        )
        ChannelDescriptionQuery = (
            Channel.Channel.query.filter(
                Channel.Channel.description.like("%" + term + "%")
            )
            .with_entities(
                Channel.Channel.id,
                Channel.Channel.channelName,
                Channel.Channel.channelLoc,
                Channel.Channel.private,
                Channel.Channel.imageLocation,
                Channel.Channel.owningUser,
                Channel.Channel.topic,
                Channel.Channel.views,
                Channel.Channel.currentViewers,
                Channel.Channel.record,
                Channel.Channel.chatEnabled,
                Channel.Channel.chatBG,
                Channel.Channel.chatTextColor,
                Channel.Channel.chatAnimation,
                Channel.Channel.offlineImageLocation,
                Channel.Channel.description,
                Channel.Channel.allowComments,
                Channel.Channel.protected,
                Channel.Channel.channelMuted,
                Channel.Channel.showChatJoinLeaveNotification,
                Channel.Channel.defaultStreamName,
                Channel.Channel.autoPublish,
                Channel.Channel.vanityURL,
            )
            .all()
        )
        ChannelTagQuery = (
            Channel.channel_tags.query.filter(
                Channel.channel_tags.name.like("%" + term + "%")
            )
            .with_entities(
                Channel.channel_tags.id,
                Channel.channel_tags.name,
                Channel.channel_tags.channelID,
            )
            .all()
        )

        ChannelTagEntryQuery = []
        for channel in ChannelTagQuery:
            ChannelTagEntryQuery = (
                Channel.Channel.query.filter_by(id=channel.channelID)
                .with_entities(
                    Channel.Channel.id,
                    Channel.Channel.channelName,
                    Channel.Channel.channelLoc,
                    Channel.Channel.private,
                    Channel.Channel.imageLocation,
                    Channel.Channel.owningUser,
                    Channel.Channel.topic,
                    Channel.Channel.views,
                    Channel.Channel.currentViewers,
                    Channel.Channel.record,
                    Channel.Channel.chatEnabled,
                    Channel.Channel.chatBG,
                    Channel.Channel.chatTextColor,
                    Channel.Channel.chatAnimation,
                    Channel.Channel.offlineImageLocation,
                    Channel.Channel.description,
                    Channel.Channel.allowComments,
                    Channel.Channel.protected,
                    Channel.Channel.channelMuted,
                    Channel.Channel.showChatJoinLeaveNotification,
                    Channel.Channel.defaultStreamName,
                    Channel.Channel.autoPublish,
                    Channel.Channel.vanityURL,
                )
                .all()
            )

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


def invalidateVideoCache(videoId):
    cachedVideo = getVideo(videoId)
    cache.delete_memoized(getVideo, videoId)
    cache.delete_memoized(getAllVideoByOwnerId, cachedVideo.owningUser)
    cache.delete_memoized(getChannelVideos, cachedVideo.channelID)

    return True


@cache.memoize(timeout=5)
def getChanneActiveStreams(channelID):
    StreamQuery = (
        Stream.Stream.query.filter_by(
            linkedChannel=channelID, active=True, complete=False
        )
        .with_entities(
            Stream.Stream.id,
            Stream.Stream.topic,
            Stream.Stream.streamName,
            Stream.Stream.startTimestamp,
            Stream.Stream.uuid,
            Stream.Stream.currentViewers,
            Stream.Stream.totalViewers,
        )
        .all()
    )
    return StreamQuery


@cache.memoize(timeout=10)
def getAllStreams():
    StreamQuery = (
        Stream.Stream.query.filter_by(active=True, complete=False)
        .join(Channel.Channel, and_(Channel.Channel.id == Stream.Stream.linkedChannel, Channel.Channel.private == False, Channel.Channel.protected == False))
        .with_entities(
            Stream.Stream.id,
            Stream.Stream.topic,
            Stream.Stream.streamName,
            Stream.Stream.startTimestamp,
            Stream.Stream.uuid,
            Stream.Stream.currentViewers,
            Stream.Stream.totalViewers,
            Channel.Channel.channelLoc,
            Channel.Channel.owningUser,
        )
        .all()
    )

    return StreamQuery


# Recorded Video Related DB Calls
@cache.memoize(timeout=60)
def getAllVideo_View(channelID):
    recordedVid = (
        RecordedVideo.RecordedVideo.query.filter_by(
            channelID=channelID, pending=False, published=True
        )
        .with_entities(
            RecordedVideo.RecordedVideo.id,
            RecordedVideo.RecordedVideo.uuid,
            RecordedVideo.RecordedVideo.videoDate,
            RecordedVideo.RecordedVideo.owningUser,
            RecordedVideo.RecordedVideo.channelName,
            RecordedVideo.RecordedVideo.channelID,
            RecordedVideo.RecordedVideo.description,
            RecordedVideo.RecordedVideo.topic,
            RecordedVideo.RecordedVideo.views,
            RecordedVideo.RecordedVideo.length,
            RecordedVideo.RecordedVideo.videoLocation,
            RecordedVideo.RecordedVideo.thumbnailLocation,
            RecordedVideo.RecordedVideo.gifLocation,
            RecordedVideo.RecordedVideo.pending,
            RecordedVideo.RecordedVideo.allowComments,
            RecordedVideo.RecordedVideo.published,
            RecordedVideo.RecordedVideo.originalStreamID,
        )
        .all()
    )
    return recordedVid


@cache.memoize(timeout=60)
def getVideo(videoID):
    recordedVid = (
        RecordedVideo.RecordedVideo.query.filter_by(id=videoID)
        .with_entities(
            RecordedVideo.RecordedVideo.id,
            RecordedVideo.RecordedVideo.uuid,
            RecordedVideo.RecordedVideo.videoDate,
            RecordedVideo.RecordedVideo.owningUser,
            RecordedVideo.RecordedVideo.channelName,
            RecordedVideo.RecordedVideo.channelID,
            RecordedVideo.RecordedVideo.description,
            RecordedVideo.RecordedVideo.topic,
            RecordedVideo.RecordedVideo.views,
            RecordedVideo.RecordedVideo.length,
            RecordedVideo.RecordedVideo.videoLocation,
            RecordedVideo.RecordedVideo.thumbnailLocation,
            RecordedVideo.RecordedVideo.gifLocation,
            RecordedVideo.RecordedVideo.pending,
            RecordedVideo.RecordedVideo.allowComments,
            RecordedVideo.RecordedVideo.published,
            RecordedVideo.RecordedVideo.originalStreamID,
        )
        .first()
    )
    return recordedVid


@cache.memoize(timeout=60)
def getAllVideoByOwnerId(ownerId):
    recordedVid = (
        RecordedVideo.RecordedVideo.query.filter_by(
            owningUser=ownerId, pending=False, published=True
        )
        .with_entities(
            RecordedVideo.RecordedVideo.id,
            RecordedVideo.RecordedVideo.uuid,
            RecordedVideo.RecordedVideo.videoDate,
            RecordedVideo.RecordedVideo.owningUser,
            RecordedVideo.RecordedVideo.channelName,
            RecordedVideo.RecordedVideo.channelID,
            RecordedVideo.RecordedVideo.description,
            RecordedVideo.RecordedVideo.topic,
            RecordedVideo.RecordedVideo.views,
            RecordedVideo.RecordedVideo.length,
            RecordedVideo.RecordedVideo.videoLocation,
            RecordedVideo.RecordedVideo.thumbnailLocation,
            RecordedVideo.RecordedVideo.gifLocation,
            RecordedVideo.RecordedVideo.pending,
            RecordedVideo.RecordedVideo.allowComments,
            RecordedVideo.RecordedVideo.published,
            RecordedVideo.RecordedVideo.originalStreamID,
        )
        .all()
    )
    return recordedVid


@cache.memoize(timeout=60)
def getAllVideo():
    recordedVid = (
        RecordedVideo.RecordedVideo.query.filter_by(pending=False, published=True)
        .join(
            Channel.Channel,
            and_(
                Channel.Channel.id == RecordedVideo.RecordedVideo.channelID,
                Channel.Channel.protected == False,
                Channel.Channel.private == False
            ),
        )
        .with_entities(
            RecordedVideo.RecordedVideo.id,
            RecordedVideo.RecordedVideo.uuid,
            RecordedVideo.RecordedVideo.videoDate,
            RecordedVideo.RecordedVideo.owningUser,
            RecordedVideo.RecordedVideo.channelName,
            RecordedVideo.RecordedVideo.channelID,
            RecordedVideo.RecordedVideo.description,
            RecordedVideo.RecordedVideo.topic,
            RecordedVideo.RecordedVideo.views,
            RecordedVideo.RecordedVideo.length,
            RecordedVideo.RecordedVideo.videoLocation,
            RecordedVideo.RecordedVideo.thumbnailLocation,
            RecordedVideo.RecordedVideo.gifLocation,
            RecordedVideo.RecordedVideo.pending,
            RecordedVideo.RecordedVideo.allowComments,
            RecordedVideo.RecordedVideo.published,
            RecordedVideo.RecordedVideo.originalStreamID,
        )
        .all()
    )
    return recordedVid


@cache.memoize(timeout=60)
def getVideoCommentCount(videoID):
    videoCommentsQuery = comments.videoComments.query.filter_by(videoID=videoID).count()
    result = videoCommentsQuery
    return result


@cache.memoize(timeout=120)
def searchVideos(term):
    if term is not None:

        VideoNameQuery = (
            RecordedVideo.RecordedVideo.query.filter(
                RecordedVideo.RecordedVideo.channelName.like("%" + term + "%"),
                RecordedVideo.RecordedVideo.published == True,
            )
            .with_entities(
                RecordedVideo.RecordedVideo.id,
                RecordedVideo.RecordedVideo.channelName,
                RecordedVideo.RecordedVideo.uuid,
                RecordedVideo.RecordedVideo.thumbnailLocation,
                RecordedVideo.RecordedVideo.owningUser,
                RecordedVideo.RecordedVideo.channelID,
                RecordedVideo.RecordedVideo.description,
                RecordedVideo.RecordedVideo.description,
                RecordedVideo.RecordedVideo.topic,
                RecordedVideo.RecordedVideo.views,
                RecordedVideo.RecordedVideo.length,
                RecordedVideo.RecordedVideo.videoLocation,
                RecordedVideo.RecordedVideo.gifLocation,
                RecordedVideo.RecordedVideo.pending,
                RecordedVideo.RecordedVideo.videoDate,
                RecordedVideo.RecordedVideo.allowComments,
                RecordedVideo.RecordedVideo.published,
                RecordedVideo.RecordedVideo.originalStreamID,
            )
            .all()
        )

        VideoDescriptionQuery = (
            RecordedVideo.RecordedVideo.query.filter(
                RecordedVideo.RecordedVideo.channelName.like("%" + term + "%"),
                RecordedVideo.RecordedVideo.published == True,
            )
            .with_entities(
                RecordedVideo.RecordedVideo.id,
                RecordedVideo.RecordedVideo.channelName,
                RecordedVideo.RecordedVideo.uuid,
                RecordedVideo.RecordedVideo.thumbnailLocation,
                RecordedVideo.RecordedVideo.owningUser,
                RecordedVideo.RecordedVideo.channelID,
                RecordedVideo.RecordedVideo.description,
                RecordedVideo.RecordedVideo.description,
                RecordedVideo.RecordedVideo.topic,
                RecordedVideo.RecordedVideo.views,
                RecordedVideo.RecordedVideo.length,
                RecordedVideo.RecordedVideo.videoLocation,
                RecordedVideo.RecordedVideo.gifLocation,
                RecordedVideo.RecordedVideo.pending,
                RecordedVideo.RecordedVideo.videoDate,
                RecordedVideo.RecordedVideo.allowComments,
                RecordedVideo.RecordedVideo.published,
                RecordedVideo.RecordedVideo.originalStreamID,
            )
            .all()
        )

        VideoTagQuery = RecordedVideo.video_tags.query.filter(
            RecordedVideo.video_tags.name.like("%" + term + "%")
        ).with_entities(
            RecordedVideo.video_tags.id,
            RecordedVideo.video_tags.name,
            RecordedVideo.video_tags.videoID,
        )

        VideoTagEntryQuery = []
        for vid in VideoTagQuery:
            VideoTagEntryQuery = (
                RecordedVideo.RecordedVideo.query.filter_by(
                    id=vid.videoID, published=True
                )
                .with_entities(
                    RecordedVideo.RecordedVideo.id,
                    RecordedVideo.RecordedVideo.channelName,
                    RecordedVideo.RecordedVideo.uuid,
                    RecordedVideo.RecordedVideo.thumbnailLocation,
                    RecordedVideo.RecordedVideo.owningUser,
                    RecordedVideo.RecordedVideo.channelID,
                    RecordedVideo.RecordedVideo.description,
                    RecordedVideo.RecordedVideo.description,
                    RecordedVideo.RecordedVideo.topic,
                    RecordedVideo.RecordedVideo.views,
                    RecordedVideo.RecordedVideo.length,
                    RecordedVideo.RecordedVideo.videoLocation,
                    RecordedVideo.RecordedVideo.gifLocation,
                    RecordedVideo.RecordedVideo.pending,
                    RecordedVideo.RecordedVideo.videoDate,
                    RecordedVideo.RecordedVideo.allowComments,
                    RecordedVideo.RecordedVideo.published,
                    RecordedVideo.RecordedVideo.originalStreamID,
                )
                .all()
            )

        resultsArray = VideoNameQuery + VideoDescriptionQuery
        resultsArray = list(set(resultsArray))
        for entry in VideoTagEntryQuery:
            if entry not in resultsArray:
                resultsArray.append(entry)

        return resultsArray
    else:
        return []


# Clip Related DB Calls
@cache.memoize(timeout=30)
def getClipChannelID(clipID):
    ClipQuery = RecordedVideo.Clips.query.filter_by(id=clipID).first()
    if ClipQuery is not None:
        RecordedVideoQuery = getVideo(ClipQuery.parentVideo)
        if RecordedVideo is not None:
            ChannelQuery = getChannel(RecordedVideoQuery.channelID)
            if ChannelQuery is not None:
                return ChannelQuery.id
    return None


@cache.memoize(timeout=60)
def getAllClipsForChannel_View(channelID):
    VideoQuery = getChannelVideos(channelID)
    clipList = []
    for vid in VideoQuery:
        clipQuery = RecordedVideo.Clips.query.filter_by(
            parentVideo=vid.id, published=True
        ).all()
        clipList = clipList + clipQuery
    return clipList


@cache.memoize(timeout=60)
def getAllClipsForUser(userId):
    videoQuery = getAllVideoByOwnerId(userId)
    videoIds = []
    for video in videoQuery:
        videoIds.append(video.id)

    clips = (
        RecordedVideo.Clips.query.filter(
            RecordedVideo.Clips.published == True,
            RecordedVideo.Clips.parentVideo.in_(videoIds),
        )
        .join(
            RecordedVideo.RecordedVideo,
            RecordedVideo.Clips.parentVideo == RecordedVideo.RecordedVideo.id,
        )
        .join(
            Channel.Channel, Channel.Channel.id == RecordedVideo.RecordedVideo.channelID
        )
        .join(Sec.User, Sec.User.id == Channel.Channel.owningUser)
        .with_entities(
            RecordedVideo.Clips.id,
            RecordedVideo.Clips.clipName,
            RecordedVideo.Clips.uuid,
            RecordedVideo.Clips.thumbnailLocation,
            Channel.Channel.owningUser,
            RecordedVideo.Clips.views,
            RecordedVideo.Clips.length,
            Channel.Channel.protected,
            Channel.Channel.channelName,
            RecordedVideo.RecordedVideo.topic,
            Sec.User.pictureLocation,
            RecordedVideo.Clips.parentVideo,
            RecordedVideo.Clips.description,
            RecordedVideo.Clips.published,
        )
        .all()
    )
    return clips


@cache.memoize(timeout=120)
def searchClips(term):
    if term is not None:
        clipNameQuery = (
            RecordedVideo.Clips.query.filter(
                RecordedVideo.Clips.clipName.like("%" + term + "%"),
                RecordedVideo.Clips.published == True,
            )
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
                RecordedVideo.Clips.clipName,
                RecordedVideo.Clips.uuid,
                RecordedVideo.Clips.thumbnailLocation,
                Channel.Channel.owningUser,
                RecordedVideo.Clips.views,
                RecordedVideo.Clips.length,
                Channel.Channel.protected,
                Channel.Channel.channelName,
                RecordedVideo.RecordedVideo.topic,
                Sec.User.pictureLocation,
                RecordedVideo.Clips.parentVideo,
            )
            .all()
        )

        clipDescriptionQuery = (
            RecordedVideo.Clips.query.filter(
                RecordedVideo.Clips.clipName.like("%" + term + "%"),
                RecordedVideo.Clips.published == True,
            )
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
                RecordedVideo.Clips.clipName,
                RecordedVideo.Clips.uuid,
                RecordedVideo.Clips.thumbnailLocation,
                Channel.Channel.owningUser,
                RecordedVideo.Clips.views,
                RecordedVideo.Clips.length,
                Channel.Channel.protected,
                Channel.Channel.channelName,
                RecordedVideo.RecordedVideo.topic,
                Sec.User.pictureLocation,
                RecordedVideo.Clips.parentVideo,
            )
            .all()
        )

        resultsArray = clipNameQuery + clipDescriptionQuery
        resultsArray = list(set(resultsArray))
        return resultsArray
    else:
        return []


# Topic Related DB Calls
@cache.memoize(timeout=120)
def getAllTopics():
    topicQuery = topics.topics.query.all()
    return topicQuery


@cache.memoize(timeout=120)
def searchTopics(term):
    if term is not None:
        topicNameQuery = (
            topics.topics.query.filter(topics.topics.name.like("%" + term + "%"))
            .with_entities(topics.topics.id, topics.topics.name)
            .all()
        )
        resultsArray = topicNameQuery
        resultsArray = list(set(resultsArray))
        return resultsArray
    else:
        return []


# User Related DB Calls
@cache.memoize(timeout=300)
def getUserPhotoLocation(userID):
    UserQuery = (
        Sec.User.query.filter_by(id=userID)
        .with_entities(Sec.User.id, Sec.User.pictureLocation)
        .first()
    )
    if UserQuery is not None:
        if UserQuery.pictureLocation is None or UserQuery.pictureLocation == "":
            return "/static/img/user2.png"
        return UserQuery.pictureLocation
    else:
        return "/static/img/user2.png"


@cache.memoize(timeout=30)
def getUser(userID):
    returnData = {}
    UserQuery = Sec.User.query.filter_by(id=userID).with_entities(Sec.User.id, Sec.User.uuid, Sec.User.username, Sec.User.biography, Sec.User.pictureLocation).first()
    if UserQuery is not None:
        OwnedChannels = getChannelsByOwnerId(UserQuery.id)
        returnData = {
            "id": str(UserQuery.id),
            "uuid": UserQuery.uuid,
            "username": UserQuery.username,
            "biography": UserQuery.biography,
            "pictureLocation": "/images/" + str(UserQuery.pictureLocation),
            "channels": OwnedChannels,
            "page": "/profile/" + str(UserQuery.username) + "/"
        }
    return Dict2Class(returnData)

@cache.memoize(timeout=30)
def getUserByUsernameDict(username):
    returnData = {}
    UserQuery = Sec.User.query.filter_by(username=username).with_entities(Sec.User.id, Sec.User.uuid, Sec.User.username, Sec.User.biography, Sec.User.pictureLocation).first()
    if UserQuery is not None:
        OwnedChannels = getChannelsByOwnerId(UserQuery.id)
        returnData = {
            "id": str(UserQuery.id),
            "uuid": UserQuery.uuid,
            "username": UserQuery.username,
            "biography": UserQuery.biography,
            "pictureLocation": "/images/" + str(UserQuery.pictureLocation),
            "channels": OwnedChannels,
            "page": "/profile/" + str(UserQuery.username) + "/"
        }
    return returnData

@cache.memoize(timeout=120)
def searchUsers(term):
    if term is not None:
        userNameQuery = (
            Sec.User.query.filter(
                Sec.User.username.like("%" + term + "%"), Sec.User.active == True
            )
            .with_entities(
                Sec.User.id, Sec.User.username, Sec.User.uuid, Sec.User.pictureLocation
            )
            .all()
        )
        userDescriptionQuery = (
            Sec.User.query.filter(
                Sec.User.biography.like("%" + term + "%"), Sec.User.active == True
            )
            .with_entities(
                Sec.User.id, Sec.User.username, Sec.User.uuid, Sec.User.pictureLocation
            )
            .all()
        )
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


@cache.memoize(timeout=1200)
def getStaticPages():
    staticPageQuery = settings.static_page.query.all()
    return staticPageQuery


@cache.memoize(timeout=1200)
def getStaticPage(pageName):
    staticPageQuery = settings.static_page.query.filter_by(name=pageName).first()
    return staticPageQuery
