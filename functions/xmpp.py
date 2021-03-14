from classes.settings import settings
from classes import Channel
from classes.Sec import User

from app import ejabberd

from globals.globalvars import room_config

def sanityCheck():
    buildMissingRooms()
    verifyExistingRooms()
    cleanInvalidRooms()
    return True

def buildMissingRooms():
    sysSettings = settings.query.first()
    channelQuery = Channel.Channel.query.all()
    for channel in channelQuery:
        try:
            xmppQuery = ejabberd.get_room_affiliations(channel.channelLoc, 'conference.' + sysSettings.siteAddress)
        except:
            print({"level": "info", "message": "Rebuilding missing ejabberd room - " + str(channel.channelLoc)})
            ejabberd.create_room(channel.channelLoc, 'conference.' + sysSettings.siteAddress, sysSettings.siteAddress)

            for key, value in room_config.items():
                ejabberd.change_room_option(channel.channelLoc, 'conference.' + sysSettings.siteAddress, key, value)

            ejabberd.set_room_affiliation(channel.channelLoc, 'conference.' + sysSettings.siteAddress, channel.owner.uuid + '@' + sysSettings.siteAddress, 'owner')

    return True

def verifyExistingRooms():
    sysSettings = settings.query.first()
    print({"level": "info", "message": "Verifying existing ejabberd Rooms"})
    for channel in Channel.Channel.query.all():
        xmppQuery = ejabberd.get_room_affiliations(channel.channelLoc, 'conference.' + sysSettings.siteAddress)

        affiliationList = []
        for affiliation in xmppQuery['affiliations']:
            user = {}
            for entry in affiliation['affiliation']:
                for key, value in entry.items():
                    user[key] = value
            affiliationList.append(user)

        for user in affiliationList:
            if user['domain'] != sysSettings.siteAddress:
                userQuery = User.query.filter_by(uuid=user['username']).first()
                if userQuery is not None:
                    ejabberd.set_room_affiliation(channel.channelLoc, 'conference.' + sysSettings.siteAddress,
                                                  userQuery.uuid + '@' + sysSettings.siteAddress, user['affiliation'])

        if not all((d['username'] == channel.owner.uuid and d['domain'] == sysSettings.siteAddress) for d in
                   affiliationList):
            ejabberd.set_room_affiliation(channel.channelLoc, 'conference.' + sysSettings.siteAddress,
                                          channel.owner.uuid + '@' + sysSettings.siteAddress, 'owner')

        if channel.protected:
            ejabberd.change_room_option(channel.channelLoc, 'conference.' + sysSettings.siteAddress, 'password_protected', 'true')
            ejabberd.change_room_option(channel.channelLoc, 'conference.' + sysSettings.siteAddress, 'password', channel.xmppToken)
        else:
            ejabberd.change_room_option(channel.channelLoc, 'conference.' + sysSettings.siteAddress, 'password', '')
            ejabberd.change_room_option(channel.channelLoc, 'conference.' + sysSettings.siteAddress, 'password_protected', 'false')


def cleanInvalidRooms():
    sysSettings = settings.query.first()
    xmppChannels = ejabberd.muc_online_rooms('global')

    roomList = []
    count = 0
    if 'rooms' in xmppChannels:
        for room in xmppChannels['rooms']:
            roomName = room['room'].replace('@conference.' + sysSettings.siteAddress,"")
            existingChannels = Channel.Channel.query.filter_by(channelLoc=roomName).first()
            if existingChannels is None:
                ejabberd.destroy_room(roomName, 'conference.' + sysSettings.siteAddress)
                count = count + 1
    print({"level": "info", "message": "Completed Pruning Invalid Rooms - " + str(count)})

def getChannelCounts(channelLoc):
    sysSettings = settings.query.first()

    roomOccupantsJSON = ejabberd.get_room_occupants_number(channelLoc, "conference." + sysSettings.siteAddress)
    currentViewers = roomOccupantsJSON['occupants']

    return currentViewers

def getChannelAffiliations(channelLoc):
    sysSettings = settings.query.first()
    roomAffiliationJSON = ejabberd.get_room_affiliations(channelLoc, 'conference.' + sysSettings.siteAddress)
    userList = {}
    for entry in roomAffiliationJSON['affiliations']:
        data = {}
        for user in entry['affiliation']:
            for key, value in user.items():
                data[key] = value
        print(data)
        userList[data['username']] = data['affiliation']
    return userList