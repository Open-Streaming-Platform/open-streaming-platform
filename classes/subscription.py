from .shared import db

class subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer, db.ForeignKey('user.id'))
    channelID = db.Column(db.Integer, db.ForeignKey('Channel.id'))

    def __init__(self, userID, channelID):
        self.userID = userID
        self.channelID = channelID

    def __repr__(self):
        return '<id %r>' % self.id