from flask import session
from flask_security import current_user
import datetime
import bleach
import logging

from classes.shared import db, limiter
from classes import Channel
from classes import Sec
from classes import invites
from classes import views
from classes import comments
from classes import apikey

from globals import globalvars

from functions import cache, system, channelFunc

log = logging.getLogger('app.functions.securityFunctions')

@limiter.limit("100/second")
def check_isValidChannelViewer(channelID):
    if current_user.is_authenticated:

        # Allow Admin
        if current_user.has_role('Admin'):
            return True

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

def flag_delete_user(userID):
    userQuery = Sec.User.query.filter_by(id=userID).first()
    if userQuery is not None:
        userQuery.active = False
        existingFlag = Sec.UsersFlaggedForDeletion.query.filter_by(userID=userQuery.id).first()
        if existingFlag is None:
            newUserFlag = Sec.UsersFlaggedForDeletion(userQuery.id)
            db.session.add(newUserFlag)
            db.session.commit()
        return True
    db.session.commit()
    db.session.close()
    return False


def delete_user(userID):
    """
    Deletes Channel Data, Comments, Videos, Clips, and Userdata for a given userID
    """
    userQuery = Sec.User.query.filter_by(id=userID).first()
    if userQuery is not None:

        userFlaggedForDeletionQuery = Sec.UsersFlaggedForDeletion.query.filter_by(userID=userQuery.id).first()
        if userFlaggedForDeletionQuery is not None:
            db.session.delete(userFlaggedForDeletionQuery)

        channelQuery = Channel.Channel.query.filter_by(owningUser=userQuery.id).all()
        username = userQuery.username

        # Delete any existing Invites
        inviteQuery = invites.invitedViewer.query.filter_by(userID=int(userID)).all()
        for invite in inviteQuery:
            db.session.delete(invite)
        db.session.commit()

        # Delete any existing User Comments
        commentQuery = comments.videoComments.query.filter_by(userID=int(userID)).all()
        for comment in commentQuery:
            db.session.delete(comment)
        db.session.commit()

        # Delete any existing API Keys
        apikeyQuery = apikey.apikey.query.filter_by(userID=userID).all()
        for key in apikeyQuery:
            db.session.delete(key)
        db.session.commit()

        # Delete Channels and all Channel Data
        for channel in channelQuery:
            channelFunc.delete_channel(channel.id)

        # Clear All Role Entries for a User Prior to Deletion
        from app import user_datastore
        roleQuery = Sec.Role.query.all()
        for role in roleQuery:
            user_datastore.remove_role_from_user(userQuery, role)

        db.session.delete(userQuery)
        db.session.commit()
        log.warning({"level": "warning", "message": "User Deleted - " + username})
        system.newLog(1, "User " + current_user.username + " deleted User " + username)
        return True
    else:
        return False

def uia_username_mapper(identity):
    # we allow pretty much anything - but we bleach it.
    return bleach.clean(identity, strip=True)