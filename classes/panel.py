from .shared import db
import json


class panel(db.Model):

    """
    OSP Content Panel
    Attributes
    ----------
        name : str
            Friendly Name of the Panel for Identification
        type : int
            Indicator of Panel Type {0: Custom Markdown, 1: Livestream List, 2: Video List, 3: Clip List, 4: Topic List}
    """
    __abstract__ = True
    name = db.Column(db.String(255))
    type = db.Column(db.Integer)
    header = db.Column(db.String(1024))
    order = db.Column(db.Integer)
    content = db.Column(db.Text)

class globalPanel(panel):
    id = db.Column(db.Integer, primary_key=True)

    def __init__(self, name, panelType, header, order, content):
        self.name = name
        self.type = panelType
        self.header = header
        self.order = order
        self.content = content

    def __repr__(self):
        return '<id %r>' % self.id

class userPanel(panel):
    id = db.Column(db.Integer, primary_key=True)

    def __init__(self, name, panelType, header, order, content):
        self.name = name
        self.type = panelType
        self.header = header
        self.order = order
        self.content = content

    def __repr__(self):
        return '<id %r>' % self.id

class panelMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pageName = db.Column(db.String(255))
    panelType = db.Column(db.Integer)
    panelId = db.Column(db.Integer)
    panelOrder = db.Column(db.Integer)

    def __init__(self, pageName, panelType, panelId, initialOrder):
        self.pageName = pageName
        self.panelType = panelType
        self.panelId = panelId
        self.panelOrder = initialOrder

    def __repr__(self):
        return '<id %r>' % self.id