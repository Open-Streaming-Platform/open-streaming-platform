from flask_security import current_user
from flask_socketio import emit
from sqlalchemy.sql.expression import func

from classes.shared import db, socketio
from classes import stickers

@socketio.on('editSticker')
def editSticker(message):
    stickerID = int(message['stickerID'])
    stickerName = str(message['stickerName'])

    if 'channelID' in message:
        # TODO Stub for Channel Level Stickers
        pass
    else:
        if current_user.has_role('admin'):
            stickerQuery = stickers.stickers.query.filter_by(id=stickerID).first()
            if stickerQuery is not None:
                stickerQuery.name = stickerName
                db.session.commit()
    db.session.close()
    return 'OK'

@socketio.on('deleteSticker')
def deleteSticker(message):
    stickerID = int(message['stickerID'])
    if 'channelID' in message:
        # TODO Stub for Channel Level Stickers
        pass
    else:
        if current_user.has_role('admin'):
            stickerQuery = stickers.stickers.query.filter_by(id=stickerID).first()
            if stickerQuery is not None:
                db.session.delete(stickerQuery)
                db.session.commit()
    db.session.close()
    return 'OK'

