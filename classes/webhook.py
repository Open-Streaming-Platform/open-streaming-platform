from .shared import db


class webhook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    channelID = db.Column(db.Integer, db.ForeignKey("Channel.id"))
    endpointURL = db.Column(db.String(2048))
    requestHeader = db.Column(db.String(4096))
    requestPayload = db.Column(db.String(4096))
    requestType = db.Column(db.Integer)
    requestTrigger = db.Column(db.Integer)

    def __init__(
        self,
        name,
        channelID,
        endpointURL,
        requestHeader,
        requestPayload,
        requestType,
        requestTrigger,
    ):
        self.name = name
        self.channelID = channelID
        self.endpointURL = endpointURL
        self.requestHeader = requestHeader
        self.requestPayload = requestPayload
        self.requestType = requestType
        self.requestTrigger = requestTrigger

    def __repr__(self):
        return "<id %r>" % self.id


class globalWebhook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    endpointURL = db.Column(db.String(2048))
    requestHeader = db.Column(db.String(4096))
    requestPayload = db.Column(db.String(4096))
    requestType = db.Column(db.Integer)
    requestTrigger = db.Column(db.Integer)

    def __init__(
        self,
        name,
        endpointURL,
        requestHeader,
        requestPayload,
        requestType,
        requestTrigger,
    ):
        self.name = name
        self.endpointURL = endpointURL
        self.requestHeader = requestHeader
        self.requestPayload = requestPayload
        self.requestType = requestType
        self.requestTrigger = requestTrigger

    def __repr__(self):
        return "<id %r>" % self.id
