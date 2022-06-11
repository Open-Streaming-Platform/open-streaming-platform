from .shared import db

class hub(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hubUUID = db.Column(db.String(255))
    hubToken = db.Column(db.String(255))

    def __init__(self, uuid, token):
        self.hubUUID = uuid
        self.hubToken = token

    def __repr__(self):
        return '<id %r>' % self.id