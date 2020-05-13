from flask_security import current_user
from flask_socketio import emit
from sqlalchemy.sql.expression import func

from classes.shared import db, socketio
from classes import Channel
from classes import invites
from classes import Sec

@socketio.on('generateInviteCode')
def generateInviteCode(message):
    selectedInviteCode = str(message['inviteCode'])
    daysToExpire = int(message['daysToExpiration'])
    channelID = int(message['chanID'])

    channelQuery = Channel.Channel.query.filter_by(id=channelID, owningUser=current_user.id).first()

    if channelQuery is not None:
        newInviteCode = invites.inviteCode(daysToExpire, channelID)
        if selectedInviteCode != "":
            inviteCodeQuery = invites.inviteCode.query.filter_by(code=selectedInviteCode).first()
            if inviteCodeQuery is None:
                newInviteCode.code = selectedInviteCode
            else:
                db.session.close()
                return False

        db.session.add(newInviteCode)
        db.session.commit()

        emit('newInviteCode', {'code': str(newInviteCode.code), 'expiration': str(newInviteCode.expiration), 'channelID':str(newInviteCode.channelID)}, broadcast=False)

    else:
        pass
    db.session.close()
    return 'OK'

@socketio.on('deleteInviteCode')
def deleteInviteCode(message):
    code = message['code']
    codeQuery = invites.inviteCode.query.filter_by(code=code).first()
    channelQuery = Channel.Channel.query.filter_by(id=codeQuery.channelID).first()
    if codeQuery is not None:
        if (channelQuery.owningUser is current_user.id) or (current_user.has_role('Admin')):
            channelID = channelQuery.id
            db.session.delete(codeQuery)
            db.session.commit()
            emit('inviteCodeDeleteAck', {'code': str(code), 'channelID': str(channelID)}, broadcast=False)
        else:
            emit('inviteCodeDeleteFail', {'code': 'fail', 'channelID': 'fail'}, broadcast=False)
    else:
        emit('inviteCodeDeleteFail', {'code': 'fail', 'channelID': 'fail'}, broadcast=False)

    db.session.close()
    return 'OK'

@socketio.on('addUserChannelInvite')
def addUserChannelInvite(message):
    channelID = int(message['chanID'])
    username = message['username']
    daysToExpire = message['daysToExpiration']

    channelQuery = Channel.Channel.query.filter_by(id=channelID, owningUser=current_user.id).first()

    if channelQuery is not None:
        invitedUserQuery = Sec.User.query.filter(func.lower(Sec.User.username) == func.lower(username)).first()
        if invitedUserQuery is not None:
            previouslyInvited = False
            for invite in invitedUserQuery.invites:
                if invite.channelID is channelID:
                    previouslyInvited = True

            if not previouslyInvited:
                newUserInvite = invites.invitedViewer(invitedUserQuery.id, channelID, daysToExpire)
                db.session.add(newUserInvite)
                db.session.commit()

                emit('invitedUserAck', {'username': username, 'added': str(newUserInvite.addedDate), 'expiration': str(newUserInvite.expiration), 'channelID': str(channelID), 'id': str(newUserInvite.id)}, broadcast=False)
                db.session.commit()
                db.session.close()
    db.session.close()
    return 'OK'

@socketio.on('deleteInvitedUser')
def deleteInvitedUser(message):
    inviteID = int(message['inviteID'])
    inviteIDQuery = invites.invitedViewer.query.filter_by(id=inviteID).first()
    channelQuery = Channel.Channel.query.filter_by(id=inviteIDQuery.channelID).first()
    if inviteIDQuery is not None:
        if (channelQuery.owningUser is current_user.id) or (current_user.has_role('Admin')):
            db.session.delete(inviteIDQuery)
            db.session.commit()
            emit('invitedUserDeleteAck', {'inviteID': str(inviteID)}, broadcast=False)
    db.session.close()
    return 'OK'