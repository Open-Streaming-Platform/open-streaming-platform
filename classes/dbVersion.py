from .shared import db


class dbVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.Float)

    def __init__(self, version):
        self.version = version

    def __repr__(self):
        return "<id %r>" % self.id
