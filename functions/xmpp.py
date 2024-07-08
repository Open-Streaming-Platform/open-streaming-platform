from collections.abc import Iterator

import logging
from flask import current_app
from classes.settings import settings
from classes import Channel
from classes.Sec import User

from functions import cachedDbCalls

from app import ejabberd

from globals.globalvars import room_config, defaultChatDomain

log = logging.getLogger("app.functions.xmpp")

def set_user_affiliation(userUuid, channelLocation, new_affil) -> None:
    ejabberd.set_room_affiliation(
        channelLocation,
        "conference." + defaultChatDomain,
        userUuid + "@" + defaultChatDomain,
        new_affil
    )

def sanityCheck() -> bool:
    buildMissingRooms()
    verifyExistingRooms()
    cleanInvalidRooms()
    return True


def buildMissingRooms() -> bool:
    sysSettings = cachedDbCalls.getSystemSettings()
    channelQuery = Channel.Channel.query.join(
        User, Channel.Channel.owningUser == User.id
    ).with_entities(Channel.Channel.channelLoc, User.uuid.label("userUUID"))
    for channel in channelQuery:
        try:
            xmppQuery = ejabberd.get_room_affiliations(
                channel.channelLoc, f"conference.{defaultChatDomain}"
            )
        except:
            log.info(
                {
                    "level": "info",
                    "message": "Rebuilding missing ejabberd room - "
                    + str(channel.channelLoc),
                }
            )

            buildRoom(channel.channelLoc, channel.userUUID)

    return True


def buildRoom(channel_loc, owner_uuid, channel_title = "", channel_desc = "") -> bool:
    ejabberd.create_room(
        channel_loc,
        f"conference.{defaultChatDomain}",
        defaultChatDomain,
    )

    for key, value in room_config.items():
        ejabberd.change_room_option(
            channel_loc,
            f"conference.{defaultChatDomain}",
            key,
            value,
        )

    if channel_title != "":
        ejabberd.change_room_option(
            channel_loc,
            f"conference.{defaultChatDomain}",
            "title",
            channel_title,
        )
    if channel_desc != "":
        ejabberd.change_room_option(
            channel_loc,
            f"conference.{defaultChatDomain}",
            "description",
            channel_desc,
        )

    ejabberd.set_room_affiliation(
        channel_loc,
        f"conference.{defaultChatDomain}",
        f"{owner_uuid}@{defaultChatDomain}",
        "owner",
    )

    return True


def verifyExistingRooms() -> None:
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
            channel.channelLoc, f"conference.{defaultChatDomain}"
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
                        f"conference.{defaultChatDomain}",
                        f"{userQuery.uuid}@{defaultChatDomain}",
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
                f"conference.{defaultChatDomain}",
                f"{channel.userUUID}@{defaultChatDomain}",
                "owner",
            )

        if channel.protected:
            ejabberd.change_room_option(
                channel.channelLoc,
                f"conference.{defaultChatDomain}",
                "password_protected",
                "true",
            )
            ejabberd.change_room_option(
                channel.channelLoc,
                f"conference.{defaultChatDomain}",
                "password",
                channel.xmppToken,
            )
        else:
            ejabberd.change_room_option(
                channel.channelLoc,
                f"conference.{defaultChatDomain}",
                "password",
                "",
            )
            ejabberd.change_room_option(
                channel.channelLoc,
                f"conference.{defaultChatDomain}",
                "password_protected",
                "false",
            )


def cleanInvalidRooms() -> None:
    sysSettings = cachedDbCalls.getSystemSettings()
    xmppChannels = ejabberd.muc_online_rooms("global")

    roomList = []
    count = 0
    if "rooms" in xmppChannels:
        for room in xmppChannels["rooms"]:
            roomName = room["room"].replace(f"@conference.{defaultChatDomain}", "")
            existingChannels = cachedDbCalls.getChannelByLoc(roomName)
            if existingChannels is None:
                ejabberd.destroy_room(roomName, f"conference.{defaultChatDomain}")
                count = count + 1
    log.info(
        {"level": "info", "message": f"Completed Pruning Invalid Rooms - {str(count)}"}
    )

def getChannelOccupants(channelLoc) -> Iterator[dict]:
    affiliations = getChannelAffiliations(channelLoc)

    for item in ejabberd.get_room_occupants(
        channelLoc, "conference." + defaultChatDomain
    )['occupants']:
        occupant = {}
        for kv_item in item['occupant']: # A list of dictionaries, each with only one key-value pair.
            for key, val in kv_item.items():
                occupant[key] = val
        
        user_uuid = occupant['jid'].split('@',1)[0]
        if cachedDbCalls.IsUserGCMByUUID(user_uuid):
            occupant['affiliation'] = 'gcm'
        elif user_uuid in affiliations:
            occupant['affiliation'] = affiliations[user_uuid]
        else:
            occupant['affiliation'] = "none"

        yield occupant

def getChannelCounts(channelLoc: str) -> int:
    sysSettings = cachedDbCalls.getSystemSettings()
    roomOccupantsJSON = ejabberd.get_room_occupants_number(
        channelLoc, f"conference.{defaultChatDomain}"
    )
    currentViewers = roomOccupantsJSON["occupants"]

    return currentViewers

def getChannelOptions(channelLoc: str) -> dict:
    optionsDict = {}

    xmppQuery = ejabberd.get_room_options(
        channelLoc, f"conference.{defaultChatDomain}"
    )
    if "options" in xmppQuery:
        for option in xmppQuery["options"]:
            key = None
            value = None
            for entry in option["option"]:
                if "name" in entry:
                    key = entry["name"]
                elif "value" in entry:
                    value = entry["value"]
            if key is not None and value is not None:
                optionsDict[key] = value

    return optionsDict

def getChannelAffiliation(channelLoc: str, user_uuid: str) -> str:
    return ejabberd.get_room_affiliation(
        channelLoc,
        f"conference.{defaultChatDomain}",
        user_uuid + "@" + defaultChatDomain
    )['affiliation']

def getChannelAffiliations(channelLoc: str) -> dict:
    sysSettings = cachedDbCalls.getSystemSettings()
    roomAffiliationJSON = ejabberd.get_room_affiliations(
        channelLoc, f"conference.{defaultChatDomain}"
    )
    userList = {}
    for entry in roomAffiliationJSON["affiliations"]:
        data = {}
        for user in entry["affiliation"]:
            for key, value in user.items():
                data[key] = value
        userList[data["username"]] = data["affiliation"]
    return userList
