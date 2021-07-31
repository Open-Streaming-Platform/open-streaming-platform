from classes import Sec
from classes import apikey
from classes.shared import db

def isValidAdminKey(requestedAPIKey):
    validKey = False
    apiKeyQuery = apikey.apikey.query.filter_by(type=2, key=requestedAPIKey).first()
    if apiKeyQuery is not None:
        if apiKeyQuery.isValid() is True:
            userID = apiKeyQuery.userID
            userQuery = Sec.User.query.filter_by(id=userID).first()
            if userQuery is not None:
                if userQuery.has_role("Admin"):
                    validKey = True
    return validKey