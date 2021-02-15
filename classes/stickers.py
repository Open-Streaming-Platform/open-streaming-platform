from .shared import db


class stickers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    channelID = db.Column(db.Integer)
    filename = db.Column(db.String(1024))

    def __init__(self, name, filename):
        self.name = name
        self.filename = filename
