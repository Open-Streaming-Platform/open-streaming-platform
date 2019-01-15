from shared import db
from binascii import hexlify
import os

def generateKey(length):
    key = hexlify(os.urandom(length))
    return key.decode()

class apikey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer,db.ForeignKey('user.id'))
    key = db.Column(db.String(255))
    type = db.Column(db.Integer)

    def __init__(self, userID, keytype):
        self.userID = userID
        self.key = generateKey(40)
        self.type = keytype

    def __repr__(self):
        return '<id %r>' % self.id