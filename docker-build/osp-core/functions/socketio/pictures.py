from flask_security import current_user
import os

from classes.shared import db, socketio
from classes import stickers

stickerLocation = "/var/www/images/stickers/"


@socketio.on("editSticker")
def editSticker(message):
    stickerID = int(message["stickerID"])
    stickerName = str(message["stickerName"])

    if "channelID" in message:
        channelID = int(message["channelID"])
        stickerQuery = stickers.stickers.query.filter_by(
            id=stickerID, channelID=channelID
        ).first()
        if stickerQuery != None:
            if stickerQuery.channel.owningUser == current_user.id:
                stickerQuery.name = stickerName
                stickerExt = (stickerQuery.filename).split(".")[1]
                newFilename = stickerName + "." + stickerExt
                os.rename(
                    stickerLocation
                    + stickerQuery.channel.channelLoc
                    + "/"
                    + stickerQuery.filename,
                    stickerLocation
                    + stickerQuery.channel.channelLoc
                    + "/"
                    + newFilename,
                )
                stickerQuery.filename = newFilename
                db.session.commit()
    else:
        if current_user.has_role("Admin"):
            stickerQuery = stickers.stickers.query.filter_by(id=stickerID).first()
            if stickerQuery is not None:
                stickerQuery.name = stickerName
                stickerExt = (stickerQuery.filename).split(".")[1]
                newFilename = stickerName + "." + stickerExt
                os.rename(
                    stickerLocation + stickerQuery.filename,
                    stickerLocation + newFilename,
                )
                stickerQuery.filename = newFilename
                db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("deleteSticker")
def deleteSticker(message):
    stickerID = int(message["stickerID"])
    if "channelID" in message:
        channelID = int(message["channelID"])
        stickerQuery = stickers.stickers.query.filter_by(
            id=stickerID, channelID=channelID
        ).first()
        if stickerQuery != None:
            if stickerQuery.channel.owningUser == current_user.id:
                try:
                    os.remove(stickerLocation + stickerQuery.filename)
                except OSError:
                    pass
                db.session.delete(stickerQuery)
                db.session.commit()
    else:
        if current_user.has_role("Admin"):
            stickerQuery = stickers.stickers.query.filter_by(id=stickerID).first()
            if stickerQuery is not None:
                try:
                    os.remove(stickerLocation + stickerQuery.filename)
                except OSError:
                    pass
                db.session.delete(stickerQuery)
                db.session.commit()
    db.session.close()
    return "OK"
