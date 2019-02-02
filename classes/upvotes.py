from .shared import db

class channelUpvotes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer)
    channelID = db.Column(db.Integer, db.ForeignKey('Channel.id'))

    def __init__(self, userID, channelID):
        self.userID = userID
        self.channelID = channelID

    def __repr__(self):
        return '<id %r>' % self.id

class streamUpvotes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer)
    streamID = db.Column(db.Integer, db.ForeignKey('Stream.id'))

    def __init__(self, userID, streamID):
        self.userID = userID
        self.streamID = streamID

    def __repr__(self):
        return '<id %r>' % self.id

class videoUpvotes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer)
    videoID = db.Column(db.Integer, db.ForeignKey('RecordedVideo.id'))

    def __init__(self, userID, videoID):
        self.userID = userID
        self.videoID = videoID

    def __repr__(self):
        return '<id %r>' % self.id