from flask import session
from flask_security import current_user
from flask_security.changeable import admin_change_password
import datetime
import bleach
import logging
import secrets

from classes.shared import db, limiter, cache
from classes import Channel
from classes import banList
from classes import subscriptions
from classes import Sec
from classes import invites
from classes import views
from classes import comments
from classes import apikey
from classes import notifications as dbclass_notif

from globals import globalvars

from functions import (
    cache as cachefunc,
    system,
    channelFunc,
    notifications,
    cachedDbCalls,
)

log = logging.getLogger("app.functions.securityFunctions")


@limiter.limit("100/second")
def check_isValidChannelViewer(channelID: int) -> bool:
    if current_user.is_authenticated:

        # Allow Admin
        if current_user.has_role("Admin"):
            return True

        # Verify if a Cached Entry Exists
        cachedResult = cachefunc.checkInviteCache(channelID)
        if cachedResult is True:
            return True
        else:
            channelQuery = (
                Channel.Channel.query.filter_by(id=channelID)
                .with_entities(Channel.Channel.owningUser)
                .first()
            )
            if channelQuery.owningUser is current_user.id:
                if channelID not in globalvars.inviteCache:
                    globalvars.inviteCache[channelID] = {}
                globalvars.inviteCache[channelID][current_user.id] = {
                    "invited": True,
                    "timestamp": datetime.datetime.utcnow(),
                }
                return True
            else:
                inviteQuery = invites.invitedViewer.query.filter_by(
                    userID=current_user.id, channelID=channelID
                ).all()
                for invite in inviteQuery:
                    if invite.isValid():
                        if channelID not in globalvars.inviteCache:
                            globalvars.inviteCache[channelID] = {}
                        globalvars.inviteCache[channelID][current_user.id] = {
                            "invited": True,
                            "timestamp": datetime.datetime.utcnow(),
                        }
                        return True
                    else:
                        db.session.delete(invite)
                        db.session.commit()
    else:
        if "inviteCodes" in session:
            inviteCodeQuery = invites.inviteCode.query.filter_by(
                channelID=channelID
            ).all()
            for code in inviteCodeQuery:
                if code.code in session["inviteCodes"]:
                    if code.isValid():
                        return True
                    else:
                        session["inviteCodes"].remove(code.code)
        else:
            session["inviteCodes"] = []
    return False


@limiter.limit("100/second")
def check_isUserValidRTMPViewer(userID: int, channelID: int) -> bool:
    userQuery = Sec.User.query.filter_by(id=userID).with_entities(Sec.User.id).first()
    if userQuery is not None:
        channelQuery = (
            Channel.Channel.query.filter_by(id=channelID)
            .with_entities(Channel.Channel.owningUser)
            .first()
        )
        if channelQuery is not None:
            if channelQuery.owningUser is userQuery.id:
                # db.session.close()
                return True
            else:
                inviteQuery = invites.invitedViewer.query.filter_by(
                    userID=userQuery.id, channelID=channelID
                ).all()
                for invite in inviteQuery:
                    if invite.isValid():
                        db.session.close()
                        return True
                    else:
                        db.session.delete(invite)
                        db.session.commit()
                        db.session.close()
    return False


def flag_delete_user(userID: int) -> bool:
    userQuery = Sec.User.query.filter_by(id=userID).first()
    if userQuery is not None:
        userQuery.active = False
        existingFlag = Sec.UsersFlaggedForDeletion.query.filter_by(
            userID=userQuery.id
        ).first()
        notifications.sendAdminNotification(
            "User "
            + userQuery.username
            + " has queued their account for deletion.  The account will be deleted in 48 from "
            + str(datetime.datetime.now()),
            "/settings/admin",
            "/images/" + str(userQuery.pictureLocation,userQuery.bannerLocation),
        )
        if existingFlag is None:
            newUserFlag = Sec.UsersFlaggedForDeletion(userQuery.id)
            db.session.add(newUserFlag)
            db.session.commit()
        return True
    db.session.commit()
    db.session.close()
    return False


def delete_user(userID: int) -> bool:
    """
    Deletes Channel Data, Comments, Videos, Clips, and Userdata for a given userID
    """
    userQuery = Sec.User.query.filter_by(id=userID).first()
    if userQuery is not None:

        userFlaggedForDeletionQuery = Sec.UsersFlaggedForDeletion.query.filter_by(
            userID=userQuery.id
        ).first()
        if userFlaggedForDeletionQuery is not None:
            db.session.delete(userFlaggedForDeletionQuery)

        username = userQuery.username

        # Delete any existing Invites
        invites.invitedViewer.query.filter_by(userID=userID).delete()
        db.session.commit()

        # Delete any existing User Comments
        comments.videoComments.query.filter_by(userID=userID).delete()
        db.session.commit()

        # Delete any existing API Keys
        apikey.apikey.query.filter_by(userID=userID).delete()
        db.session.commit()

        # Delete user's ban list entry and banned messages.
        banList.banList.query.filter_by(userID=userID).delete()
        banList.messageBanList.query.filter_by(userID=userID).delete()
        banList.messageBanList.query.filter_by(messageFrom=userID).delete()
        db.session.commit()

        # Delete messages sent TO the user, and user's notifications.
        dbclass_notif.userNotification.query.filter_by(userID=userID).delete()
        dbclass_notif.userMessage.query.filter_by(toUserID=userID).delete()
        db.session.commit()

        # Delete user's subscriptions to channels.
        subscriptions.channelSubs.query.filter_by(userID=userID).delete()
        db.session.commit()

        # Delete Channels and all Channel Data. This handles Clips + Videos too.
        channelQuery = Channel.Channel.query.filter_by(owningUser=userID).with_entities(Channel.Channel.id).all()
        for channel in channelQuery:
            channelFunc.delete_channel(channel.id)

        # Clear All Role Entries for a User Prior to Deletion
        from app import user_datastore

        # Explcitly query user's roles, for removal.
        roleQuery = userQuery.roles
        for role in roleQuery:
            user_datastore.remove_role_from_user(userQuery, role)

        db.session.delete(userQuery)
        db.session.commit()

        cache.delete_memoized(cachedDbCalls.getUser, userID)

        if current_user != None:
            runningUser = current_user.username
        else:
            runningUser = "SYSTEM"


        log.warning({"level": "warning", "message": "User Deleted - " + username})
        system.newLog(1, "User " + runningUser + " deleted User " + username)
        return True
    else:
        return False


def uia_username_mapper(identity):
    # we allow pretty much anything - but we bleach it.
    return bleach.clean(identity, strip=True)

def admin_force_reset(userId: int) -> bool:
    UserQuery = Sec.User.query.filter_by(id=userId).first()
    if UserQuery != None:
        if UserQuery.authType == 0:
            randomPass = secrets.token_urlsafe(32)
            admin_change_password(UserQuery, randomPass, notify=True)
            db.session.commit()
            return True
    db.session.commit()
    return False
