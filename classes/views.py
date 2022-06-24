from .shared import db

import datetime


class views(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime)
    viewType = db.Column(
        db.Integer
    )  # View Type of 0 indicates Live Streams, 1 indicated Video View
    itemID = db.Column(
        db.Integer
    )  # If View Type is 0, this values will be the associated Channel.ID that was streaming, 1 is the RecordedVideo.id

    def __init__(self, viewType, itemID):
        self.viewType = viewType
        self.itemID = itemID
        self.date = datetime.datetime.utcnow()

    def __repr__(self):
        return "<id %r>" % self.id
