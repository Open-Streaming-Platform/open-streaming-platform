from .shared import db
import datetime
from binascii import hexlify
import os

def generateKey(length):
    key = hexlify(os.urandom(length))
    return key.decode()

class invitedViewer(db.Model):
    __tablename__ = 'invitedViewer'
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer, db.ForeignKey('user.id'))
    channelID = db.Column(db.Integer, db.ForeignKey('Channel.id'))
    addedDate = db.Column(db.DateTime)
    expiration = db.Column(db.DateTime)
    inviteCode = db.Column(db.Integer, db.ForeignKey('inviteCode.id'))

    def __init__(self, userID, channelID, expirationDays, inviteCode=None):
        self.userID = userID
        self.channelID = channelID
        self.addedDate = datetime.datetime.utcnow()
        if inviteCode is not None:
            self.inviteCode = inviteCode

        if int(expirationDays) <= 0:
            self.expiration = None
        else:
            self.expiration = datetime.datetime.utcnow() + datetime.timedelta(days=int(expirationDays))

    def __repr__(self):
        return '<id %r>' % self.id

    def isValid(self):
        now = datetime.datetime.utcnow()
        if self.expiration is None:
            return True
        elif now < self.expiration:
            return True
        else:
            return False

class inviteCode(db.Model):
    __tablename__ = 'inviteCode'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(255), unique=True)
    expiration = db.Column(db.DateTime)
    channelID = db.Column(db.Integer, db.ForeignKey('Channel.id'))
    uses = db.Column(db.Integer)
    viewers = db.relationship('invitedViewer', backref='usedCode', lazy="joined")

    def __init__(self, expirationDays, channelID):
        self.code = generateKey(12)
        self.channelID = channelID
        self.uses = 0

        if int(expirationDays) <= 0:
            self.expiration = None
        else:
            self.expiration = datetime.datetime.utcnow() + datetime.timedelta(days=int(expirationDays))

    def __repr__(self):
        return '<id %r>' % self.id

    def isValid(self):
        now = datetime.datetime.utcnow()
        if self.expiration is None:
            return True
        elif now < self.expiration:
            return True
        else:
            return False
