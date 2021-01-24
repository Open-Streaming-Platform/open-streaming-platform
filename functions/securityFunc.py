from flask import session
from flask_security import current_user
import datetime

from classes.shared import db, limiter
from classes import Channel
from classes import Sec
from classes import invites

from globals import globalvars

from functions import cache

@limiter.limit("100/second")
def check_isValidChannelViewer(channelID):
    if current_user.is_authenticated:
        # Verify if a Cached Entry Exists
        cachedResult = cache.checkInviteCache(channelID)
        if cachedResult is True:
            return True
        else:
            channelQuery = Channel.Channel.query.filter_by(id=channelID).with_entities(Channel.Channel.owningUser).first()
            if channelQuery.owningUser is current_user.id:
                if channelID not in globalvars.inviteCache:
                    globalvars.inviteCache[channelID] = {}
                globalvars.inviteCache[channelID][current_user.id] = {"invited": True, "timestamp": datetime.datetime.utcnow()}
                return True
            else:
                inviteQuery = invites.invitedViewer.query.filter_by(userID=current_user.id, channelID=channelID).all()
                for invite in inviteQuery:
                    if invite.isValid():
                        if channelID not in globalvars.inviteCache:
                            globalvars.inviteCache[channelID] = {}
                        globalvars.inviteCache[channelID][current_user.id] = {"invited": True, "timestamp": datetime.datetime.utcnow()}
                        return True
                    else:
                        db.session.delete(invite)
                        db.session.commit()
    else:
        if 'inviteCodes' in session:
            inviteCodeQuery = invites.inviteCode.query.filter_by(channelID=channelID).all()
            for code in inviteCodeQuery:
                if code.code in session['inviteCodes']:
                    if code.isValid():
                        return True
                    else:
                        session['inviteCodes'].remove(code.code)
        else:
            session['inviteCodes'] = []
    return False

@limiter.limit("100/second")
def check_isUserValidRTMPViewer(userID,channelID):
    userQuery = Sec.User.query.filter_by(id=userID).with_entities(Sec.User.id).first()
    if userQuery is not None:
        channelQuery = Channel.Channel.query.filter_by(id=channelID).with_entities(Channel.Channel.owningUser).first()
        if channelQuery is not None:
            if channelQuery.owningUser is userQuery.id:
                #db.session.close()
                return True
            else:
                inviteQuery = invites.invitedViewer.query.filter_by(userID=userQuery.id, channelID=channelID).all()
                for invite in inviteQuery:
                    if invite.isValid():
                        db.session.close()
                        return True
                    else:
                        db.session.delete(invite)
                        db.session.commit()
                        db.session.close()
    return False