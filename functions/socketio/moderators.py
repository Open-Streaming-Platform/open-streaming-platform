from flask_security import current_user
from flask_socketio import emit
from sqlalchemy.sql.expression import func

from classes.shared import db, socketio
from classes import Channel
from classes import Sec

@socketio.on('addMod')
def addMod(message):

    if str(message['JID']).split('@')[1]:
        JID = str(message['JID'])
    else:
        userQuery = Sec.User.query.filter(func.lower(Sec.User.username) == func.lower(JID.split('@')[0])).first()
        if userQuery is not None:
            JID = str(message['JID']) + {{sysSettings.siteAddress}}

    channelLoc = str(message['ChannelLoc'])
    channelQuery = Channel.Channel.query.filter_by(channelLoc=ChannelLoc, owningUser=current_user.id).first()

    if channelQuery is not None and JID != "":
        from app import ejabberd
        ejabberd.set_room_affiliation(channelLoc, 'conference.' + sysSettings.siteAddress, JID, 'admin')
        emit('addMod', {'mod': str(JID),  'channelLoc':str(channelLoc)}, broadcast=False)
    else:
        pass
    return 'OK'

@socketio.on('deleteMod')
def deleteMod(message):
    JID = str(message['JID'])
    channelLoc = str(message['ChannelLoc'])

    channelQuery = Channel.Channel.query.filter_by(channelLoc=ChannelLoc, owningUser=current_user.id).first()

    user = JID.split('@')[0]
    userQuery = Sec.User.query.filter(func.lower(Sec.User.username) == func.lower(user)).first()

    if channelQuery is not None:
        if userQuery and current_user != user:
            from app import ejabberd
            ejabberd.set_room_affiliation(channelLoc, 'conference.' + sysSettings.siteAddress, JID, 'member')
            emit('deleteMod', {'mod': str(JID),  'channelLoc':str(channelLoc)}, broadcast=False)
        elif userQuery is None:
            from app import ejabberd
            ejabberd.set_room_affiliation(channelLoc, 'conference.' + sysSettings.siteAddress, JID, 'None')
            emit('deleteMod', {'mod': str(JID),  'channelLoc':str(channelLoc)}, broadcast=False)
    else:
        pass
    return 'OK'