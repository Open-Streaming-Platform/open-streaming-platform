from shared import db
from binascii import hexlify
import os
import datetime

def generateKey(length):
    key = hexlify(os.urandom(length))
    return key.decode()

class apikey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String)
    userID = db.Column(db.Integer,db.ForeignKey('user.id'))
    key = db.Column(db.String(255))
    type = db.Column(db.Integer)

    def __init__(self, userID, keytype, description, expirationDays):
        self.userID = userID
        self.key = generateKey(40)
        self.type = keytype
        self.description = description
        self.createdOn = datetime.datetime.now()

        if expirationDays == 0:
            self.expiration = None
        else:
            self.expiration = datetime.datetime.now() + datetime.timedelta(days=expirationDays)

    def __repr__(self):
        return '<id %r>' % self.id

    def isValid(self):
        now = datetime.datetime.now()
        if now > self.expiration:
            return True
        else:
            return False