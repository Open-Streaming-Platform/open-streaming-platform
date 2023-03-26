from .shared import db
import uuid
import os
from functions import cachedDbCalls


class Channel(db.Model):
    __tablename__ = "Channel"
    id = db.Column(db.Integer, primary_key=True)
    owningUser = db.Column(db.Integer, db.ForeignKey("user.id"))
    streamKey = db.Column(db.String(255), unique=True)
    channelName = db.Column(db.String(255))
    channelLoc = db.Column(db.String(255), unique=True)
    topic = db.Column(db.Integer)
    views = db.Column(db.Integer)
    currentViewers = db.Column(db.Integer)
    record = db.Column(db.Boolean)
    chatEnabled = db.Column(db.Boolean)
    chatBG = db.Column(db.String(255))
    chatTextColor = db.Column(db.String(10))
    chatAnimation = db.Column(db.String(255))
    imageLocation = db.Column(db.String(255))
    offlineImageLocation = db.Column(db.String(255))
    description = db.Column(db.String(4096))
    allowComments = db.Column(db.Boolean)
    protected = db.Column(db.Boolean)
    channelMuted = db.Column(db.Boolean)
    private = db.Column(db.Boolean)
    showChatJoinLeaveNotification = db.Column(db.Boolean)
    defaultStreamName = db.Column(db.String(255))
    autoPublish = db.Column(db.Boolean)
    rtmpRestream = db.Column(db.Boolean)
    rtmpRestreamDestination = db.Column(db.String(4096))
    xmppToken = db.Column(db.String(64))
    vanityURL = db.Column(db.String(1024))
    allowGuestNickChange = db.Column(db.Boolean)
    showHome = db.Column(db.Boolean)
    maxVideoRetention = db.Column(db.Integer)
    stream = db.relationship(
        "Stream", backref="channel", cascade="all, delete-orphan", lazy="joined"
    )
    recordedVideo = db.relationship(
        "RecordedVideo", backref="channel", cascade="all, delete-orphan", lazy="joined"
    )
    upvotes = db.relationship(
        "channelUpvotes", backref="stream", cascade="all, delete-orphan", lazy="joined"
    )
    inviteCodes = db.relationship(
        "inviteCode", backref="channel", cascade="all, delete-orphan", lazy="joined"
    )
    invitedViewers = db.relationship(
        "invitedViewer", backref="channel", cascade="all, delete-orphan", lazy="joined"
    )
    subscriptions = db.relationship(
        "channelSubs", backref="channel", cascade="all, delete-orphan", lazy="joined"
    )
    webhooks = db.relationship(
        "webhook", backref="channel", cascade="all, delete-orphan", lazy="joined"
    )
    restreamDestinations = db.relationship(
        "restreamDestinations",
        backref="channelData",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    chatStickers = db.relationship(
        "stickers", backref="channel", cascade="all, delete-orphan", lazy="joined"
    )
    panels = db.relationship(
        "channelPanel", backref="channel", cascade="all, delete-orphan", lazy="joined"
    )
    tags = db.relationship(
        "channel_tags", backref="channel", cascade="all, delete-orphan", lazy="joined"
    )
    chatFormat = db.Column(db.String(16))
    chatHistory = db.Column(db.Integer)

    def __init__(
        self,
        owningUser,
        streamKey,
        channelName,
        topic,
        record,
        chatEnabled,
        allowComments,
        showHome,
        description,
    ):
        self.owningUser = owningUser
        self.streamKey = streamKey
        self.channelName = channelName
        self.description = description
        self.topic = topic
        self.channelLoc = str(uuid.uuid4())
        self.record = record
        self.allowComments = allowComments
        self.chatEnabled = chatEnabled
        self.chatBG = "Standard"
        self.chatTextColor = "#FFFFFF"
        self.chatAnimation = "slide-in-left"
        self.views = 0
        self.currentViewers = 0
        self.protected = False
        self.channelMuted = False
        self.showChatJoinLeaveNotification = True
        self.defaultStreamName = ""
        self.autoPublish = True
        self.rtmpRestream = False
        self.rtmpRestreamDestination = ""
        self.xmppToken = str(os.urandom(32).hex())
        self.vanityURL = None
        self.allowGuestNickChange = True
        self.showHome = showHome
        self.maxVideoRetention = 0
        self.private = False
        self.chatFormat = "messenger"
        self.chatHistory = 2
        self.hubEnabled = False
        self.hubNSFW = False
        

    def __repr__(self):
        return "<id %r>" % self.id

    def get_upvotes(self):
        return len(self.upvotes)

    def get_videos(self):
        return cachedDbCalls.getChannelVideos(self.id)

    def get_streams(self):
        return cachedDbCalls.getChannelStreamIds(self.id)

    def get_tags(self):
        return cachedDbCalls.getChannelTagIds(self.id)

    def serialize(self):
        return {
            "id": self.id,
            "channelEndpointID": self.channelLoc,
            "owningUser": self.owningUser,
            "owningUsername": self.owner.username,
            "channelName": self.channelName,
            "description": self.description,
            "channelImage": "/images/" + str(self.imageLocation),
            "offlineImageLocation": "/images/" + str(self.offlineImageLocation),
            "topic": self.topic,
            "views": self.views,
            "currentViews": self.currentViewers,
            "recordingEnabled": self.record,
            "chatEnabled": self.chatEnabled,
            "stream": [obj.id for obj in self.get_streams()],
            "recordedVideoIDs": [obj.id for obj in self.get_videos()],
            "upvotes": self.get_upvotes(),
            "protected": self.protected,
            "allowGuestNickChange": self.allowGuestNickChange,
            "vanityURL": self.vanityURL,
            "showHome": self.showHome,
            "maxVideoRetention": self.maxVideoRetention,
            "subscriptions": self.subscriptions.count(),
            "tags": [obj.id for obj in self.get_tags()],
        }

    def authed_serialize(self):
        return {
            "id": self.id,
            "channelEndpointID": self.channelLoc,
            "owningUser": self.owningUser,
            "channelName": self.channelName,
            "description": self.description,
            "channelImage": "/images/" + str(self.imageLocation),
            "offlineImageLocation": "/images/" + str(self.offlineImageLocation),
            "topic": self.topic,
            "views": self.views,
            "currentViews": self.currentViewers,
            "recordingEnabled": self.record,
            "chatEnabled": self.chatEnabled,
            "stream": [obj.id for obj in self.get_streams()],
            "recordedVideoIDs": [obj.id for obj in self.get_videos()],
            "upvotes": self.get_upvotes(),
            "protected": self.protected,
            "xmppToken": self.xmppToken,
            "streamKey": self.streamKey,
            "allowGuestNickChange": self.allowGuestNickChange,
            "vanityURL": self.vanityURL,
            "showHome": self.showHome,
            "maxVideoRetention": self.maxVideoRetention,
            "subscriptions": self.subscriptions.count(),
            "tags": [obj.id for obj in self.get_tags()],
        }


class channel_tags(db.Model):
    __tablename__ = "channel_tags"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    channelID = db.Column(db.Integer, db.ForeignKey("Channel.id"))
    taggedByUser = db.Column(db.Integer)

    def __init__(self, tagName, channelID, userID):
        self.name = tagName
        self.channelID = channelID
        self.taggedByUser = userID

    def __repr__(self):
        return "<id %r>" % self.id


class restreamDestinations(db.Model):
    __tablename__ = "restreamDestinations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    channel = db.Column(db.Integer, db.ForeignKey("Channel.id"))
    enabled = db.Column(db.Boolean)
    url = db.Column(db.String(4096))

    def __init__(self, channel, name, url):
        self.channel = int(channel)
        self.name = name
        self.enabled = False
        self.url = url

    def serialize(self):
        return {
            "id": self.id,
            "channel": self.channelData.channelLoc,
            "name": self.name,
            "enabled": self.enabled,
            "url": self.url,
        }

    def __repr__(self):
        return "<id %r>" % self.id
