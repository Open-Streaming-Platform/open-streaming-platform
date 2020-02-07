from .shared import db

class logs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    message = db.Column(db.String(1024))
    type = db.Column(db.Integer)

    def __init__(self, timestamp, message, logType):
        self.timestamp = timestamp
        self.message = message
        self.type = logType

    def __repr__(self):
        return '<id %r>' % self.id