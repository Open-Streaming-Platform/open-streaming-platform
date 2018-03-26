from app import db

class stream(db.Model):
    __tablename__="stream"
    id = db.Column(db.Integer, primary_key=True)
    streamKey = db.Column(db.String)
    streamUser = db.Column(db.String(4))

    def __init__(self, streamKey, streamUser):
        self.streamKey = streamKey
        self.streamUser = streamUser

    def __repr__(self):
        return '<id %r>' % self.id