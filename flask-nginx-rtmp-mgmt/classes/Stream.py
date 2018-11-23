import os

basedir = os.path.abspath(os.path.dirname(__file__))
from app import db

class Stream(db.Model):
    __tablename__ = "Stream"
    id = db.Column(db.Integer, primary_key=True)
    linkedChannel = db.Column(db.Integer,db.ForeignKey('Channel.id'))
    streamKey = db.Column(db.String(255))
    streamName = db.Column(db.String(255))
    topic = db.Column(db.Integer)
    currentViewers = db.Column(db.Integer)
    totalViewers = db.Column(db.Integer)
    upvotes = db.relationship('streamUpvotes', backref='stream', lazy="joined")

    def __init__(self, streamKey, streamName, linkedChannel, topic):
        self.streamKey = streamKey
        self.streamName = streamName
        self.linkedChannel = linkedChannel
        self.currentViewers = 0
        self.totalViewers = 0
        self.topic = topic

    def __repr__(self):
        return '<id %r>' % self.id

    def get_upvotes(self):
        return self.upvotes.count()

    def add_viewer(self):
        self.currentViewers = self.currentViewers + 1
        db.session.commit()

    def remove_viewer(self):
        self.currentViewers = self.currentViewers - 1
        db.session.commit()

    def serialize(self):
        return {
            'id': self.id,
            'linkedChannel': self.linkedChannel,
            'streamName': self.streamName,
            'topic': self.topic,
            'currentViewers': self.currentViewers,
            'totalViewers': self.currentViewers,
            'upvotes': self.get_upvotes()
        }