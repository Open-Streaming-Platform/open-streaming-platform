from .shared import db
from uuid import uuid4
from datetime import datetime

class userNotification(db.Model):
    __tablename__ = "userNotification"
    id = db.Column(db.Integer,primary_key=True)
    notificationID = db.Column(db.String(255), unique=True)
    timestamp = db.Column(db.DateTime)
    message = db.Column(db.String(1024))
    link = db.Column(db.String(1024))
    image = db.Column(db.String(256))
    userID = db.Column(db.Integer, db.ForeignKey('user.id'))
    read = db.Column(db.Boolean)

    def __init__(self, message, link, image, userID):
        self.notificationID = str(uuid4())
        self.timestamp = datetime.utcnow()
        self.message = message
        self.link = link
        self.image = image
        self.userID = userID
        self.read = False

    def __repr__(self):
        return '<id %r>' % self.id