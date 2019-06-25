from .shared import db

class pushRegistration(db.Model):
    __tablename__ = 'pushRegistration'
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer, db.ForeignKey('user.id'))
    subscription_token = db.Column(db.String(400), unique=True)
    endpointID = db.Column(db.String(300))

    def __init__(self, userID, endpointID, subscription_token):
        self.userID = userID
        self.subscription_token = subscription_token
        self.endpointID = endpointID

    def __repr__(self):
        return '<id %r>' % self.id

class channelSubscription(db.Model):
    __tablename__ = 'channelSubscription'
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer, db.ForeignKey('user.id'))
    channelID = db.Column(db.Integer, db.ForeignKey('Channel.id'))

    def __init__(self, userID, channelID):
        self.userID = userID
        self.channelID = channelID

    def __repr__(self):
        return '<id %r>' % self.id