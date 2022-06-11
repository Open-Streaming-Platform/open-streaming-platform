from .shared import db

class banList(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    channelLoc = db.Column(db.String(255))
    userID = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __init__(self,channelLoc,userID):
        self.channelLoc = channelLoc
        self.userID = userID

    def __repr__(self):
        return '<id %r>' % self.id

class ipList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ipAddress = db.Column(db.String(1024))
    reason = db.Column(db.String(1024))

    def __init__(self, ipAddress, reason="None"):
        self.ipAddress = ipAddress
        self.reason = reason

    def __repr__(self):
        return '<id %r>' % self.id

class channelBanList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channelLoc = db.Column(db.String(255))
    username = db.Column(db.String(255))
    userUUID = db.Column(db.String(255))

    def __init__(self, channelLoc, username, userUUID):
        self.channelLoc = channelLoc
        self.username = username
        self.userUUID = userUUID

    def __repr__(self):
        return '<id %r>' % self.id

class messageBanList(db.Model):
    __tablename__ = "messageBanList"
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer, db.ForeignKey('user.id'))
    messageFrom = db.Column(db.Integer)

    def __init__(self, userID, messageFrom):
        self.userID = userID
        self.messageFrom = messageFrom

    def __repr__(self):
        return '<id %r>' % self.id

class chatBannedWords(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(1028))

    def __init__(self, word):
        self.word = word

    def __repr__(self):
        return '<id %r>' % self.id

class chatBannedMessages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    msgID = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime)
    channelLoc = db.Column(db.String(255))

    def __init__(self, msgID, timestamp, channelLoc):
        self.msgID = msgID
        self.timestamp = timestamp
        self.channelLoc = channelLoc

    def __repr__(self):
        return '<id %r>' % self.id