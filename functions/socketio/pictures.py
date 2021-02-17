from flask_security import current_user
import os

from classes.shared import db, socketio
from classes import stickers

stickerLocation = "/var/www/images/stickers/"

@socketio.on('editSticker')
def editSticker(message):
    stickerID = int(message['stickerID'])
    stickerName = str(message['stickerName'])

    if 'channelID' in message:
        # TODO Stub for Channel Level Stickers
        pass
    else:
        if current_user.has_role('Admin'):
            stickerQuery = stickers.stickers.query.filter_by(id=stickerID).first()
            if stickerQuery is not None:
                stickerQuery.name = stickerName
                stickerExt = (stickerQuery.filename).split('.')[1]
                newFilename = stickerName + '.' + stickerExt
                os.rename(stickerLocation + stickerQuery.filename, stickerLocation + newFilename)
                stickerQuery.filename = newFilename
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
        if current_user.has_role('Admin'):
            stickerQuery = stickers.stickers.query.filter_by(id=stickerID).first()
            if stickerQuery is not None:
                try:
                    os.remove(stickerLocation + stickerQuery.filename)
                except OSError:
                    pass
                db.session.delete(stickerQuery)
                db.session.commit()
    db.session.close()
    return 'OK'

