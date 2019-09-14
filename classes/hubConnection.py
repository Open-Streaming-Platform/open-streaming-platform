from .shared import db
from secrets import token_hex

class hubServers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    serverAddress = db.Column(db.String(2056))
    status = db.Column(db.Integer)
    connections = db.relationship('hubConnection', backref='server', lazy="joined")

    def __init__(self, serverAddress):
        self.serverAddress = serverAddress
        self.status = 0

    def __repr__(self):
        return '<id %r>' % self.id

class hubConnection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    verificationToken = db.Column(db.String(2056))
    serverToken = db.Column(db.String(2056))
    hubServer = db.Column(db.Integer, db.ForeignKey('hubServers.id'))
    status = db.Column(db.Integer)

    def __init__(self, hubServer):
        self.hubServer = hubServer
        self.verificationToken = token_hex(256)
        self.status = 0

    def validateHub(self, serverToken):
        self.serverToken = serverToken
        self.status = 1

    def __repr__(self):
        return '<id %r>' % self.id