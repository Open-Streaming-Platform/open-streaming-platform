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
            Indicator of Panel Type {0: Custom Markdown...}
    """
    __abstract__ = True
    name = db.Column(db.String(255))
    type = db.Column(db.Integer)
    header = db.Column(db.String(1024))
    header_bg_color = db.Column(db.String(128))
    header_text_color = db.Column(db.String(128))
    body_bg_color = db.Column(db.String(128))
    body_text_color = db.Column(db.String(128))
    order = db.Column(db.Integer)
    content = db.Column(db.Text)

class globalPanel(panel):
    id = db.Column(db.Integer, primary_key=True)

    def __init__(self, name, panelType, header, header_bg_color, header_text_color, body_bg_color, body_text_color, order, content):
        self.name = name
        self.type = panelType
        self.header = header
        self.header_bg_color = header_bg_color
        self.header_text_color = header_text_color
        self.body_bg_color = body_bg_color
        self.body_text_color = body_text_color
        self.order = order
        self.content = content

    def __repr__(self):
        return '<id %r>' % self.id

class userPanel(panel):
    id = db.Column(db.Integer, primary_key=True)

    def __init__(self, name, panelType, header, header_bg_color, header_text_color, body_bg_color, body_text_color, order, content):
        self.name = name
        self.type = panelType
        self.header = header
        self.header_bg_color = header_bg_color
        self.header_text_color = header_text_color
        self.body_bg_color = body_bg_color
        self.body_text_color = body_text_color
        self.order = order
        self.content = content

    def __repr__(self):
        return '<id %r>' % self.id

class panelMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pageName = db.Column(db.String(255))
    panelType = db.Column(db.Integer)
    panelId = db.Column(db.Integer)

    def __init__(self, pageName, panelType, panelId):
        self.pageName = pageName
        self.panelType = panelType
        self.panelId = panelId

    def __repr__(self):
        return '<id %r>' % self.id