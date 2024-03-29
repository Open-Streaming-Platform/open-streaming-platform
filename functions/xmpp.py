import logging
from flask import current_app
from classes.settings import settings
from classes import Channel
from classes.Sec import User

from functions import cachedDbCalls

from app import ejabberd

from globals.globalvars import room_config, defaultChatDomain

log = logging.getLogger("app.functions.xmpp")


def sanityCheck():
    buildMissingRooms()
    verifyExistingRooms()
    cleanInvalidRooms()
    return True


def buildMissingRooms():
    sysSettings = cachedDbCalls.getSystemSettings()
    channelQuery = Channel.Channel.query.join(
        User, Channel.Channel.owningUser == User.id
    ).with_entities(Channel.Channel.channelLoc, User.uuid.label("userUUID"))
    for channel in channelQuery:
        try:
            xmppQuery = ejabberd.get_room_affiliations(
                channel.channelLoc, "conference." + defaultChatDomain
            )
        except:
            log.info(
                {
                    "level": "info",
                    "message": "Rebuilding missing ejabberd room - "
                    + str(channel.channelLoc),
                }
            )
            ejabberd.create_room(
                channel.channelLoc,
                "conference." + defaultChatDomain,
                defaultChatDomain,
            )

            for key, value in room_config.items():
                ejabberd.change_room_option(
                    channel.channelLoc,
                    "conference." + defaultChatDomain,
                    key,
                    value,
                )

            ejabberd.set_room_affiliation(
                channel.channelLoc,
                "conference." + defaultChatDomain,
                channel.userUUID + "@" + defaultChatDomain,
                "owner",
            )

    return True


def verifyExistingRooms():
    sysSettings = cachedDbCalls.getSystemSettings()
    log.info({"level": "info", "message": "Verifying existing ejabberd Rooms"})
    channelQuery = Channel.Channel.query.join(
        User, Channel.Channel.owningUser == User.id
    ).with_entities(
        Channel.Channel.channelLoc,
        Channel.Channel.xmppToken,
        Channel.Channel.protected,
        User.uuid.label("userUUID"),
    )
    for channel in channelQuery:
        xmppQuery = ejabberd.get_room_affiliations(
            channel.channelLoc, "conference." + defaultChatDomain
        )

        affiliationList = []
        for affiliation in xmppQuery["affiliations"]:
            user = {}
            for entry in affiliation["affiliation"]:
                for key, value in entry.items():
                    user[key] = value
            affiliationList.append(user)

        for user in affiliationList:
            if user["domain"] != defaultChatDomain:
                userQuery = User.query.filter_by(uuid=user["username"]).first()
                if userQuery is not None:
                    ejabberd.set_room_affiliation(
                        channel.channelLoc,
                        "conference." + defaultChatDomain,
                        userQuery.uuid + "@" + defaultChatDomain,
                        user["affiliation"],
                    )

        if not all(
            (
                d["username"] == channel.userUUID
                and d["domain"] == defaultChatDomain
            )
            for d in affiliationList
        ):
            ejabberd.set_room_affiliation(
                channel.channelLoc,
                "conference." + defaultChatDomain,
                channel.userUUID + "@" + defaultChatDomain,
                "owner",
            )

        if channel.protected:
            ejabberd.change_room_option(
                channel.channelLoc,
                "conference." + defaultChatDomain,
                "password_protected",
                "true",
            )
            ejabberd.change_room_option(
                channel.channelLoc,
                "conference." + defaultChatDomain,
                "password",
                channel.xmppToken,
            )
        else:
            ejabberd.change_room_option(
                channel.channelLoc,
                "conference." + defaultChatDomain,
                "password",
                "",
            )
            ejabberd.change_room_option(
                channel.channelLoc,
                "conference." + defaultChatDomain,
                "password_protected",
                "false",
            )


def cleanInvalidRooms():
    sysSettings = cachedDbCalls.getSystemSettings()
    xmppChannels = ejabberd.muc_online_rooms("global")

    roomList = []
    count = 0
    if "rooms" in xmppChannels:
        for room in xmppChannels["rooms"]:
            roomName = room["room"].replace(
                "@conference." + defaultChatDomain, ""
            )
            existingChannels = cachedDbCalls.getChannelByLoc(roomName)
            if existingChannels is None:
                ejabberd.destroy_room(roomName, "conference." + defaultChatDomain)
                count = count + 1
    log.info(
        {"level": "info", "message": "Completed Pruning Invalid Rooms - " + str(count)}
    )


def getChannelCounts(channelLoc):
    sysSettings = cachedDbCalls.getSystemSettings()
    roomOccupantsJSON = ejabberd.get_room_occupants_number(
        channelLoc, "conference." + defaultChatDomain
    )
    currentViewers = roomOccupantsJSON["occupants"]

    return currentViewers


def getChannelAffiliations(channelLoc):
    sysSettings = cachedDbCalls.getSystemSettings()
    roomAffiliationJSON = ejabberd.get_room_affiliations(
        channelLoc, "conference." + defaultChatDomain
    )
    userList = {}
    for entry in roomAffiliationJSON["affiliations"]:
        data = {}
        for user in entry["affiliation"]:
            for key, value in user.items():
                data[key] = value
        userList[data["username"]] = data["affiliation"]
    return userList
