from flask_security import current_user
from flask_socketio import emit, join_room
from sqlalchemy.sql.expression import func
from sqlalchemy import asc
import datetime

from classes.shared import db, socketio
from classes import Channel
from classes import Sec
from classes import settings
from classes import banList

from functions import xmpp
from functions import cachedDbCalls


@socketio.on("addMod")
def addMod(message):
    sysSettings = cachedDbCalls.getSystemSettings()
    JID = None
    username = str(message["JID"])
    userQuery = Sec.User.query.filter(
        func.lower(Sec.User.username) == func.lower(username)
    ).first()
    if userQuery is not None:
        JID = userQuery.uuid + "@" + sysSettings.siteAddress

    channelLoc = str(message["channelLoc"])
    channelQuery = Channel.Channel.query.filter_by(
        channelLoc=channelLoc, owningUser=current_user.id
    ).first()

    if channelQuery is not None and JID is not None:
        from app import ejabberd

        ejabberd.set_room_affiliation(
            channelLoc, "conference." + sysSettings.siteAddress, JID, "admin"
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
    else:
        pass
    db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("deleteMod")
def deleteMod(message):
    sysSettings = cachedDbCalls.getSystemSettings()
    JID = str(message["JID"])
    channelLoc = str(message["channelLoc"])

    channelQuery = Channel.Channel.query.filter_by(
        channelLoc=channelLoc, owningUser=current_user.id
    ).first()

    user = JID.split("@")[0]

    if channelQuery is not None:
        from app import ejabberd

        ejabberd.set_room_affiliation(
            channelLoc, "conference." + sysSettings.siteAddress, JID, "none"
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
    if current_user.is_authenticated:
        if "channelLoc" in message:
            from app import ejabberd

            channelLoc = str(message["channelLoc"])
            channelQuery = Channel.Channel.query.filter_by(
                channelLoc=channelLoc
            ).first()
            if channelQuery is not None:
                user = Sec.User.query.filter_by(id=current_user.id).first()
                channelAffiliations = xmpp.getChannelAffiliations(channelLoc)
                if user.uuid in channelAffiliations:
                    userAffiliation = channelAffiliations[user.uuid]
                    if userAffiliation == "owner" or userAffiliation == "admin":
                        banUsername = str(message["banUsername"])
                        banUserUUID = str(message["banUserUUID"])
                        existingBan = banList.channelBanList.query.filter_by(
                            userUUID=banUserUUID, channelLoc=channelLoc
                        ).first()
                        if existingBan is None:
                            newBan = banList.channelBanList(
                                channelLoc, banUsername, banUserUUID
                            )
                            db.session.add(newBan)
                            db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("unbanUser")
def socketio_xmpp_unbanUser(message):
    if current_user.is_authenticated:
        if "channelLoc" in message:
            from app import ejabberd

            channelLoc = str(message["channelLoc"])
            channelQuery = Channel.Channel.query.filter_by(
                channelLoc=channelLoc
            ).first()
            if channelQuery is not None:
                user = Sec.User.query.filter_by(id=current_user.id).first()
                channelAffiliations = xmpp.getChannelAffiliations(channelLoc)
                if user.uuid in channelAffiliations:
                    userAffiliation = channelAffiliations[user.uuid]
                    if userAffiliation == "owner" or userAffiliation == "admin":
                        unbanUserUUID = str(message["userUUID"])
                        existingBanQuery = banList.channelBanList.query.filter_by(
                            channelLoc=channelLoc, userUUID=unbanUserUUID
                        ).first()
                        if existingBanQuery is not None:
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
    if current_user.is_authenticated:
        if "channelLoc" in message and "messageId" in message:
            from app import ejabberd

            messageId = str(message["messageId"])
            channelLoc = str(message["channelLoc"])
            timestamp = datetime.datetime.utcnow()
            channelQuery = Channel.Channel.query.filter_by(
                channelLoc=channelLoc
            ).first()
            if channelQuery is not None:
                user = Sec.User.query.filter_by(id=current_user.id).first()
                channelAffiliations = xmpp.getChannelAffiliations(channelLoc)
                if user.uuid in channelAffiliations:
                    userAffiliation = channelAffiliations[user.uuid]
                    if userAffiliation == "owner" or userAffiliation == "admin":
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
