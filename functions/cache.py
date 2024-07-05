from flask_security import current_user
import datetime
import logging

from globals import globalvars
from classes.shared import db

log = logging.getLogger("app.functions.database")

# Handles the Invite Cache to cut down on SQL Calls
def checkInviteCache(channelID: int) -> bool:
    """Compares Current Users if Existing Within a given channels Invite Cache

    Args:
        channelID (int): Channel Identifier

    Returns:
        bool: Returns if current used is authorized per the Channel's Invite Cache
    """
    if current_user.is_authenticated:
        if channelID in globalvars.inviteCache:
            if current_user.id in globalvars.inviteCache[channelID]:
                if globalvars.inviteCache[channelID][current_user.id]["invited"]:
                    if datetime.datetime.utcnow() < globalvars.inviteCache[channelID][current_user.id]["timestamp"] + datetime.timedelta(minutes=10):
                        db.session.close()
                        return True
                    else:
                        globalvars.inviteCache[channelID].pop(current_user.id, None)
    db.session.close()
    return False
