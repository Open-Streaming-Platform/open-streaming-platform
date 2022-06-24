from .shared import db
from binascii import hexlify
import os
import datetime


def generateKey(length):
    key = hexlify(os.urandom(length))
    return key.decode()


class apikey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255))
    userID = db.Column(db.Integer, db.ForeignKey("user.id"))
    key = db.Column(db.String(255))
    type = db.Column(db.Integer)
    createdOn = db.Column(db.DateTime)
    expiration = db.Column(db.DateTime)

    def __init__(self, userID, keytype, description, expirationDays):
        self.userID = userID
        self.key = generateKey(40)
        self.type = keytype
        self.description = description
        self.createdOn = datetime.datetime.utcnow()

        if int(expirationDays) <= 0:
            self.expiration = None
        else:
            self.expiration = datetime.datetime.utcnow() + datetime.timedelta(
                days=int(expirationDays)
            )

    def __repr__(self):
        return "<id %r>" % self.id

    def isValid(self):
        now = datetime.datetime.utcnow()
        if self.expiration is None:
            return True
        elif now < self.expiration:
            return True
        else:
            return False
