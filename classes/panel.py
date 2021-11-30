from .shared import db
import json


class globalPanel(db.Model):

    """
    Global OSP Content Panel
    Attributes
    ----------
        name : str
            Friendly Name of the Panel for Identification
        type : int
            Indicator of Panel Type {0: Custom Markdown...}
        content : text
            Text String of JSON content structured as follows:
                {
                    Header (str): Panel Header Value
                    Header_BG_Color (str): Color Hex Value of Header Background.  If set to just #, will take Theme Value
                    Header_Text_Color (str): Color Hex Value of Header Text.  If set to just #, will take Theme Value
                    Body_BG_Color (str): Color Hex Value of Body Background.  If set to just #, will take Theme Value
                    Body_Text_Color (str): Color Hex Value of Body Text.  If set to just #, will take Theme Value
                    Order (int): Video/Stream/Clip Order
                    Markdown (str): Content Text in Markdown Format
                }
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    type = db.Column(db.Integer)
    content = db.Column(db.Text)

    def __init__(self, name, type, content):
        self.name = name
        self.type = type
        self.content = json.dumps(content)

    def __repr__(self):
        return '<id %r>' % self.id

    def getContent(self):
        return json.loads(self.content)

    def updateContent(self, content):
        self.content = json.dumps(content)
        return True
