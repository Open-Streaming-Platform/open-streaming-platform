from .shared import db


class topics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    iconClass = db.Column(db.String(255))

    def __init__(self, name, iconClass):
        self.name = name
        self.iconClass = iconClass

    def __repr__(self):
        return "<id %r>" % self.id

    def serialize(self):
        return {"id": self.id, "name": self.name}
