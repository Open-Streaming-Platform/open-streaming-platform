from .shared import db

class hubConnection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    verificationToken = db.Column(db.String(2056))
    serverToken = db.Column(db.String(2056))
    status = db.Column(db.Integer)

    def __init__(self, verificationToken):
        self.verificationToken = verificationToken
        self.status = 0

    def validateHub(self, serverToken):
        self.serverToken = serverToken
        self.status = 1

    def __repr__(self):
        return '<id %r>' % self.id