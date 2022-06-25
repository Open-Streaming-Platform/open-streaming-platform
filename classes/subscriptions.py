from .shared import db


class channelSubs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channelID = db.Column(db.Integer, db.ForeignKey("Channel.id"))
    userID = db.Column(db.Integer, db.ForeignKey("user.id"))

    def __init__(self, channelID, userID):
        self.channelID = channelID
        self.userID = userID

    def __repr__(self):
        return "<id %r>" % self.id
