from .shared import db

import datetime


class logs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    message = db.Column(db.String(1024))
    type = db.Column(db.Integer)

    def __init__(self, timestamp, message, logType):
        self.timestamp = timestamp
        self.message = message
        self.type = logType

    def __repr__(self):
        return "<id %r>" % self.id


class streamHistory(db.Model):
    __tablename__ = "streamHistory"
    id = db.Column(db.Integer, primary_key=True)
    streamUUID = db.Column(db.String(255))
    streamerID = db.Column(db.Integer)
    streamerName = db.Column(db.String(255))
    channelID = db.Column(db.Integer)
    channelName = db.Column(db.String(255))
    streamName = db.Column(db.String(255))
    startTime = db.Column(db.DateTime)
    endTime = db.Column(db.DateTime)
    length = db.Column(db.Integer)
    viewers = db.Column(db.Integer)
    upvotes = db.Column(db.Integer)
    recorded = db.Column(db.Boolean)
    recordedVideoID = db.Column(db.Integer)
    topicID = db.Column(db.Integer)
    topicName = db.Column(db.String(255))

    def __init__(
        self,
        streamUUID,
        streamerID,
        streamerName,
        channelID,
        channelName,
        streamName,
        startTime,
        endTime,
        viewers,
        upvotes,
        recorded,
        topicID,
        topicName,
        recordedVideoID,
    ):
        self.streamUUID = streamUUID
        self.streamerID = streamerID
        self.streamerName = streamerName
        self.channelID = channelID
        self.channelName = channelName
        self.streamName = streamName
        self.startTime = startTime
        self.endTime = endTime
        self.length = int((endTime - startTime).total_seconds())
        self.viewers = viewers
        self.upvotes = upvotes
        self.recorded = recorded
        if recordedVideoID is not None:
            self.recordedVideoID = recordedVideoID
        self.topicID = topicID
        self.topicName = topicName

    def __repr__(self):
        return "<id %r>" % self.id
