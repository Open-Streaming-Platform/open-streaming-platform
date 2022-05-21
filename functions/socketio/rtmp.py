from flask import abort
from flask_security import current_user

from classes.shared import db, socketio
from classes import settings

@socketio.on('toggleOSPRTMP')
def toggleRTMPServer(message):
    if current_user.has_role('Admin'):
        rtmpID = int(message['rtmpID'])
        rtmpQuery = settings.rtmpServer.query.filter_by(id=rtmpID).first()
        if rtmpQuery is not None:
            rtmpQuery.active = not rtmpQuery.active
            db.session.commit()
            db.session.close()
            return 'OK'
        else:
            db.session.commit()
            db.session.close()
            return abort(500)
    else:
        db.session.commit()
        db.session.close()
        return abort(401)

@socketio.on('toggleHideOSPRTMP')
def toggleHideRTMPServer(message):
    if current_user.has_role('Admin'):
        rtmpID = int(message['rtmpID'])
        rtmpQuery = settings.rtmpServer.query.filter_by(id=rtmpID).first()
        if rtmpQuery is not None:
            rtmpQuery.hide = not rtmpQuery.hide
            db.session.commit()
            db.session.close()
            return 'OK'
        else:
            db.session.commit()
            db.session.close()
            return abort(500)
    else:
        db.session.commit()
        db.session.close()
        return abort(401)

@socketio.on('deleteOSPRTMP')
def deleteRTMPServer(message):
    if current_user.has_role('Admin'):
        rtmpID = int(message['rtmpID'])
        rtmpQuery = settings.rtmpServer.query.filter_by(id=rtmpID).first()
        if rtmpQuery is not None:
            db.session.delete(rtmpQuery)
            db.session.commit()
            db.session.close()
            return 'OK'
        else:
            db.session.commit()
            db.session.close()
            return abort(500)
    else:
        db.session.commit()
        db.session.close()
        return abort(401)
