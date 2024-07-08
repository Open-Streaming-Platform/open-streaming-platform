from flask_security import current_user
from flask_socketio import emit, join_room
from sqlalchemy.sql.expression import func
from sqlalchemy import asc
import datetime
from json import dumps as json_dumps

from classes.shared import db, socketio
from classes import Channel
from classes import Sec
from classes import settings
from classes import banList

from functions import xmpp
from functions import cachedDbCalls

from globals import globalvars

@socketio.on("getChannelOccups")
def getChannelOccups(message):
    channelLoc = str(message["channelLoc"])
    if cachedDbCalls.getChannelIDFromLocation(channelLoc) is None:
        return "Channel does not exist."

    final_list = []
    for occupant in xmpp.getChannelOccupants(channelLoc):
        final_list.append(occupant)

    emit(
        "channelOccups",
        json_dumps(final_list),
        broadcast=False,
    )

    return "OK"

@socketio.on("statusTrueAffil")
def statusTrueAffil(message):
    if "channelLoc" not in message:
        return "No channel provided"
    if "uuid" not in message:
        return "No uuid provided"

    channelLoc = str(message["channelLoc"])
    user_uuid = str(message["uuid"])

    true_affil = 'none'
    if cachedDbCalls.IsUserGCMByUUID(user_uuid):
        true_affil = 'gcm'
    else:
        true_affil = xmpp.getChannelAffiliation(channelLoc, user_uuid)

    emit(
        "trueAffilUpdate",
        true_affil,
        broadcast=False,
    )

    return "OK"

@socketio.on("addMod")
def addMod(message):
    if not current_user.is_authenticated:
        return "Must be logged in."

    sysSettings = cachedDbCalls.getSystemSettings()
    JID = None
    username = str(message["JID"])
    userQuery = Sec.User.query.filter(
        func.lower(Sec.User.username) == func.lower(username)
    ).first()
    if userQuery is None:
        db.session.close()
        return f"'{username}' does not exist."
    
    if cachedDbCalls.IsUserGCMByUUID(userQuery.uuid):
        db.session.close()
        return "Cannot add a Global Chat Mod"
    
    JID = userQuery.uuid + "@" + globalvars.defaultChatDomain

    channelLoc = str(message["channelLoc"])
    channelQuery = Channel.Channel.query.filter_by(
        channelLoc=channelLoc, owningUser=current_user.id
    ).first()

    if channelQuery is None:
        db.session.close()
        return "Channel does not exist."
    
    if channelQuery.owningUser == userQuery.id:
        db.session.close()
        return "You're already the channel's owner."
    
    xmpp.set_user_affiliation(
        userQuery.uuid,
        channelLoc,
        "admin"
    )

    emit(
        "addMod",
        {
            "mod": str(JID),
            "channelLoc": str(channelLoc),
            "username": str(userQuery.username),
        },
        broadcast=False,
    )

    db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("deleteMod")
def deleteMod(message):
    if not current_user.is_authenticated:
        return "Must be logged in."

    sysSettings = cachedDbCalls.getSystemSettings()
    JID = str(message["JID"])
    user_uuid = JID.split("@",1)[0]

    if cachedDbCalls.IsUserGCMByUUID(user_uuid):
        db.session.close()
        return "Cannot de-mod a Global Chat Mod"

    channelLoc = str(message["channelLoc"])

    channelQuery = Channel.Channel.query.filter_by(
        channelLoc=channelLoc, owningUser=current_user.id
    ).first()

    if channelQuery is None:
        db.session.close()
        return "Channel does not exist."

    xmpp.set_user_affiliation(
        user_uuid,
        channelLoc,
        "member"
    )

    emit(
        "deleteMod",
        {"mod": str(JID), "channelLoc": str(channelLoc)},
        broadcast=False,
    )

    db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("banUser")
def socketio_xmpp_banUser(message):
    if not current_user.is_authenticated:
        return "Must be logged in."

    if "channelLoc" not in message:
        db.session.close()
        return "Cannot find channel"

    channelLoc = str(message["channelLoc"])
    channelQuery = cachedDbCalls.getChannelByLoc(channelLoc)
    if channelQuery is None:
        db.session.close()
        return "Channel does not exist."

    if not xmpp.have_admin_authority(channelQuery):
        db.session.close()
        return "Not authorized to ban users"

    banUsername = str(message["banUsername"])
    banUserUUID = None

    targetQuery = Sec.User.query.filter_by(
        username=banUsername
    ).with_entities(Sec.User.id, Sec.User.uuid).first()
    is_registered = targetQuery is not None
    if not is_registered:
        # May still be a Guest; check if banUserUUID is in the message.
        if "banUserUUID" not in message:
            return f"'{banUsername}' does not exist"

        banUserUUID = str(message["banUserUUID"])
    else:
        banUserUUID = targetQuery.uuid

    if current_user.uuid == banUserUUID:
        db.session.close()
        return "Cannot ban yourself."

    if is_registered:
        if channelQuery.owningUser == targetQuery.id:
            db.session.close()
            return "Cannot ban the Channel Owner"

        if cachedDbCalls.IsUserGCMByUUID(banUserUUID):
            db.session.close()
            return "Cannot ban a Global Chat Mod"

    if banList.channelBanList.query.filter_by(
        userUUID=banUserUUID, channelLoc=channelLoc
    ).with_entities(banList.channelBanList.id).first() is not None:
        db.session.close()
        return "That user is already banned."

    xmpp.set_user_affiliation(banUserUUID, channelLoc, "outcast")
    newBan = banList.channelBanList(
        channelLoc, banUsername, banUserUUID
    )
    db.session.add(newBan)
    db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("unbanUser")
def socketio_xmpp_unbanUser(message):
    if not current_user.is_authenticated:
        return "Must be logged in."

    if "channelLoc" not in message:
        db.session.close()
        return "Cannot find channel"

    channelLoc = str(message["channelLoc"])
    channelQuery = cachedDbCalls.getChannelByLoc(channelLoc)
    if channelQuery is None:
        db.session.close()
        return "Channel does not exist."

    if not xmpp.have_admin_authority(channelQuery):
        db.session.close()
        return "Not authorized to un-ban users"

    unbanUserUUID = str(message["userUUID"])

    existingBanQuery = banList.channelBanList.query.filter_by(
        channelLoc=channelLoc, userUUID=unbanUserUUID
    ).first()
    if existingBanQuery is None:
        db.session.close()
        return "That user is already un-banned."
    
    new_affil = "none"
    if Sec.User.query.filter_by(
        uuid=unbanUserUUID
    ).with_entities(Sec.User.id).first() is not None:
        new_affil = "member"
        
    xmpp.set_user_affiliation(unbanUserUUID, channelLoc, new_affil)
    db.session.delete(existingBanQuery)
    db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("getBanList")
def socketio_xmpp_getBanList(message):
    bannedUserList = []
    if "channelLoc" in message:
        channelLoc = str(message["channelLoc"])
        channelQuery = Channel.Channel.query.filter_by(channelLoc=channelLoc).first()
        if channelQuery is not None:
            channelBanListQuery = banList.channelBanList.query.filter_by(
                channelLoc=channelLoc
            ).all()
            bannedUserList = []
            for entry in channelBanListQuery:
                newEntry = {"username": entry.username, "useruuid": entry.userUUID}
                bannedUserList.append(newEntry)

    emit("returnBanList", {"results": bannedUserList}, broadcast=False)
    return "OK"


@socketio.on("deleteMessageRequest")
def deleteMessageRequest(message):
    if not current_user.is_authenticated:
        return "Must be logged in."

    if "channelLoc" not in message:
        db.session.close()
        return "No channel location"

    channelLoc = str(message["channelLoc"])
    channelQuery = cachedDbCalls.getChannelByLoc(channelLoc)
    if channelQuery is None:
        db.session.close()
        return "Channel does not exist"

    if not xmpp.have_admin_authority(channelQuery):
        db.session.close()
        return "Not authorized to delete messages"

    if "messageId" not in message:
        db.session.close()
        return "No message to delete"
    messageId = str(message["messageId"])

    if "messageUser" not in message:
        db.session.close()
        return "No user with that message"
    messagerUsername = str(message["messageUser"])

    userQuery = Sec.User.query.filter_by(
        username=messagerUsername
    ).with_entities(Sec.User.id, Sec.User.uuid).first()

    # Messages belonging to existing users should be double-checked before deletion.
    if userQuery is not None:
        # You may delete your own message.
        if current_user.id != userQuery.id:
            if not cachedDbCalls.IsUserGCMByUUID(current_user.uuid):
                if channelQuery.owningUser == userQuery.id:
                    db.session.close()
                    return "Cannot delete Channel Owner's message."

                if cachedDbCalls.IsUserGCMByUUID(userQuery.uuid):
                    db.session.close()
                    return "Cannot delete Global Chat Mod's message."

    timestamp = datetime.datetime.utcnow()

    newBannedMessage = banList.chatBannedMessages(
        messageId, timestamp, channelLoc
    )
    db.session.add(newBannedMessage)
    db.session.commit()

    banListOverflowQuery = (
        banList.chatBannedMessages.query.filter_by(
            channelLoc=channelLoc
        ).count()
    )
    if banListOverflowQuery > 20:
        banListOverflowMessageQuery = (
            banList.chatBannedMessages.query.filter_by(
                channelLoc=channelLoc
            )
            .order_by(banList.chatBannedMessages.timestamp.asc())
            .first()
        )
        if banListOverflowMessageQuery != None:
            db.session.delete(banListOverflowMessageQuery)
            db.session.commit()
    emit("deleteMessage", messageId, broadcast=True)
    db.session.close()
    return "OK"
