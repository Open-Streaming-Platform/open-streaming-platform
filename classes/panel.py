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
    target = db.Column(db.Integer)
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
    userId = db.Column(db.Integer)

    def __init__(self, name, userId, panelType, header, order, content):
        self.name = name
        self.userId = userId
        self.type = panelType
        self.header = header
        self.order = order
        self.content = content

    def __repr__(self):
        return '<id %r>' % self.id

class channelPanel(panel):
    __tablename__ = "channelPanel"
    id = db.Column(db.Integer, primary_key=True)
    channelId = db.Column(db.Integer, db.ForeignKey('Channel.id'))

    def __init__(self, name, channelId, panelType, header, order, content):
        self.name = name
        self.channelId = channelId
        self.type = panelType
        self.header = header
        self.order = order
        self.content = content

    def __repr__(self):
        return '<id %r>' % self.id

class panelMapping(db.Model):

    """
    OSP Content Panel Mapping
    Attributes
    ----------
        pageName : str
            html file name where the panel appears
        panelType : int
            Indicator of Panel Type {0: Global, 1: User, 2: Channel}
        panelId : int
            ID value of the panel
        panelOrder : int
            Ordering of the panel as it appears on the pageName page
        panelLocationId: int
            Identifies the unique page/user/channel/etc based on the pageName.  This value is required to map to a Channel/LivePage/User/etc when couples with the correct pageName.
    """

    id = db.Column(db.Integer, primary_key=True)
    pageName = db.Column(db.String(255))
    panelType = db.Column(db.Integer)
    panelId = db.Column(db.Integer)
    panelOrder = db.Column(db.Integer)
    panelLocationId = db.Column(db.Integer)

    def __init__(self, pageName, panelType, panelId, initialOrder, panelLocationId=0):
        self.pageName = pageName
        self.panelType = panelType
        self.panelId = panelId
        self.panelOrder = initialOrder
        self.panelLocationId = panelLocationId

    def __repr__(self):
        return '<id %r>' % self.id