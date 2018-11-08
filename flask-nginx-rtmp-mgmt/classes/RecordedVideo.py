import os
import datetime

basedir = os.path.abspath(os.path.dirname(__file__))
from app import db

class RecordedVideo(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    videoDate = db.Column(db.DateTime)
    owningUser = db.Column(db.Integer,db.ForeignKey('user.id'))
    channelName = db.Column(db.String(255))
    channelID = db.Column(db.Integer,db.ForeignKey('Channel.id'))
    topic = db.Column(db.Integer)
    views = db.Column(db.Integer)
    length = db.Column(db.Float)
    videoLocation = db.Column(db.String(255))
    thumbnailLocation = db.Column(db.String(255))
    pending = db.Column(db.Boolean)

    def __init__(self,owningUser,channelID,channelName,topic,views,videoLocation):
        self.videoDate = datetime.datetime.now()
        self.owningUser=owningUser
        self.channelID=channelID
        self.channelName=channelName
        self.topic=topic
        self.views=views
        self.videoLocation=videoLocation
        self.pending = True

    def __repr__(self):
        return '<id %r>' % self.id

    def serialize(self):
        return {
            'id': self.id,
            'videoDate': self.videoDate,
            'channelName': self.channelName,
            'topic': self.topic,
            'views': self.views,
            'length': self.length
        }