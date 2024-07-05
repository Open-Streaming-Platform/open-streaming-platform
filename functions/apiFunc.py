import logging
from typing import Union

from classes import Sec
from classes import apikey
from classes.shared import db

log = logging.getLogger("app.functions.apiFunc")

def isValidAdminKey(requestedAPIKey: str) -> bool:
    """Verifies an API Key as an Admin API Key

    Args:
        requestedAPIKey (str): API key making Request

    Returns:
        bool: Return on if key is a valid Admin API key or not
    """
    validKey = False
    apiKeyQuery: Union[apikey.apikey, None] = apikey.apikey.query.filter_by(type=2, key=requestedAPIKey).first()
    if apiKeyQuery is not None:
        if apiKeyQuery.isValid() is True:
            userID: int = apiKeyQuery.userID
            userQuery: Union[Sec.User, None] = Sec.User.query.filter_by(id=userID).first()
            if userQuery is not None:
                if userQuery.has_role("Admin"):
                    validKey = True
    return validKey
