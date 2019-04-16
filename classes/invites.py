from .shared import db
import datetime

class inviteCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(255), unique=True)
    expiration = db.Column(db.DateTime)
    channelID = db.Column(db.Integer, db.ForeignKey('Channel.id'))
    uses = db.Column(db.Integer)
    viewers = db.relationship('invitedViewer', backref='usedCode', lazy="joined")

    def __init__(self, code, expirationDays, channelID):
        self.code = code
        self.channelID = channelID

        if int(expirationDays) <= 0:
            self.expiration = None
        else:
            self.expiration = datetime.datetime.now() + datetime.timedelta(days=int(expirationDays))

    def __repr__(self):
        return '<id %r>' % self.id

    def isValid(self):
        now = datetime.datetime.now()
        if self.expiration is None:
            return True
        elif now < self.expiration:
            return True
        else:
            return False

class invitedViewer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer, db.ForeignKey('user.id'))
    channelID = db.Column(db.Integer, db.ForeignKey('Channel.id'))
    addedDate = db.Column(db.DateTime)
    expiration = db.Column(db.DateTime)
    inviteCode = db.Column(db.Integer,db.ForeignKey('inviteCode.id'))

    def __init__(self, userID, channelID, expirationDays, inviteCode=None):
        self.userID = userID
        self.channelID = channelID
        self.addedDate = datetime.datetime.now()
        if inviteCode is not None:
            self.inviteCode = inviteCode

        if int(expirationDays) <= 0:
            self.expiration = None
        else:
            self.expiration = datetime.datetime.now() + datetime.timedelta(days=int(expirationDays))

    def __repr__(self):
        return '<id %r>' % self.id

    def isValid(self):
        now = datetime.datetime.now()
        if self.expiration is None:
            return True
        elif now < self.expiration:
            return True
        else:
            return False
