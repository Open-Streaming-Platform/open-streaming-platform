from .shared import db


class channelUpvotes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer)
    channelID = db.Column(db.Integer, db.ForeignKey("Channel.id"))

    def __init__(self, userID, channelID):
        self.userID = userID
        self.channelID = channelID

    def __repr__(self):
        return "<id %r>" % self.id


class streamUpvotes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer)
    streamID = db.Column(db.Integer, db.ForeignKey("Stream.id"))

    def __init__(self, userID, streamID):
        self.userID = userID
        self.streamID = streamID

    def __repr__(self):
        return "<id %r>" % self.id


class videoUpvotes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer)
    videoID = db.Column(db.Integer, db.ForeignKey("RecordedVideo.id"))

    def __init__(self, userID, videoID):
        self.userID = userID
        self.videoID = videoID

    def __repr__(self):
        return "<id %r>" % self.id


class clipUpvotes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer)
    clipID = db.Column(db.Integer, db.ForeignKey("Clips.id"))

    def __init__(self, userID, clipID):
        self.userID = userID
        self.clipID = clipID

    def __repr__(self):
        return "<id %r>" % self.id


class commentUpvotes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer)
    commentID = db.Column(db.Integer, db.ForeignKey("videoComments.id"))

    def __init__(self, userID, commentID):
        self.userID = userID
        self.commentID = commentID

    def __repr__(self):
        return "<id %r>" % self.id
