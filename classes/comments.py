from .shared import db
from datetime import datetime


class videoComments(db.Model):
    __tablename__ = "videoComments"
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer, db.ForeignKey("user.id"))
    timestamp = db.Column(db.DateTime)
    comment = db.Column(db.String(2048))
    videoID = db.Column(db.Integer, db.ForeignKey("RecordedVideo.id"))
    upvotes = db.relationship(
        "commentUpvotes",
        backref="videoComment",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    def __init__(self, userID, comment, videoID):
        self.userID = userID
        self.timestamp = datetime.utcnow()
        self.comment = comment
        self.videoID = videoID

    def __repr__(self):
        return "<id %r>" % self.id
