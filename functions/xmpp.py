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
            ejabberd.create_room(channel.channelLoc, 'conference.' + sysSettings.siteAddress, sysSettings.siteAddress)

            for key, value in room_config.items():
                ejabberd.change_room_option(channel.channelLoc, 'conference.' + sysSettings.siteAddress, key, value)

            ejabberd.set_room_affiliation(channel.channelLoc, 'conference.' + sysSettings.siteAddress, channel.owner.username + '@' + sysSettings.siteAddress, 'owner')

            for invite in channel.invitedViewers:
                ejabberd.set_room_affiliation(channel.channelLoc, 'conference.' + sysSettings.siteAddress, invite.user.username + '@' + sysSettings.siteAddress, 'member')
    return True

def verifyExistingRooms():
    sysSettings = settings.query.first()
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
                userQuery = User.query.filter_by(username=user['username']).first()
                if userQuery is not None:
                    ejabberd.set_room_affiliation(channel.channelLoc, 'conference.' + sysSettings.siteAddress,
                                                  userQuery.username + '@' + sysSettings.siteAddress, user['affiliation'])

        if not all((d['username'] == channel.owner.username and d['domain'] == sysSettings.siteAddress) for d in
                   affiliationList):
            ejabberd.set_room_affiliation(channel.channelLoc, 'conference.' + sysSettings.siteAddress,
                                          channel.owner.username + '@' + sysSettings.siteAddress, 'owner')

        for invite in channel.invitedViewers:
            if not all((d['username'] == invite.user.username and d['affiliation'] == 'member') for d in affiliationList):
                ejabberd.set_room_affiliation(channel.channelLoc, 'conference.' + sysSettings.siteAddress,
                                              invite.user.username + '@' + sysSettings.siteAddress, 'member')

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
    print('Invalid Rooms Pruned: ' + count )
