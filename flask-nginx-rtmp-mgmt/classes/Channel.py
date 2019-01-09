import os
import uuid

basedir = os.path.abspath(os.path.dirname(__file__))
from app import db

class Channel(db.Model):
    __tablename__ = "Channel"
    id = db.Column(db.Integer, primary_key=True)
    owningUser = db.Column(db.Integer, db.ForeignKey('user.id'))
    streamKey = db.Column(db.String(255), unique=True)
    channelName = db.Column(db.String(255))
    channelLoc = db.Column(db.String(255), unique=True)
    topic = db.Column(db.Integer)
    views = db.Column(db.Integer)
    record = db.Column(db.Boolean)
    chatEnabled = db.Column(db.Boolean)
    imageLocation = db.Column(db.String(255))
    stream = db.relationship('Stream', backref='channel', lazy="joined")
    recordedVideo = db.relationship('RecordedVideo', backref='channel', lazy="joined")
    upvotes = db.relationship('channelUpvotes', backref='stream', lazy="joined")

    def __init__(self, owningUser, streamKey, channelName, topic, record, chatEnabled):
        self.owningUser = owningUser
        self.streamKey = streamKey
        self.channelName = channelName
        self.topic = topic
        self.channelLoc = str(uuid.uuid4())
        self.record = record
        self.chatEnabled = chatEnabled
        self.views = 0

    def __repr__(self):
        return '<id %r>' % self.id

    def get_upvotes(self):
        return len(self.upvotes)

    def serialize(self):
        return {
            'id': self.id,
            'channelEndpointID': self.channelLoc,
            'owningUser': self.owningUser,
            'channelName': self.channelName,
            'topic': self.topic,
            'views': self.views,
            'recordingEnabled': self.record,
            'chatEnabled': self.chatEnabled,
            'stream': [obj.serialize() for obj in self.stream],
            'recordedVideoIDs': [obj.serialize() for obj in self.recordedVideo],
            'upvotes': self.get_upvotes()
        }