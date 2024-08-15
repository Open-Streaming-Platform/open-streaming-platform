from flask_security import current_user
import os

from classes.shared import db, socketio
from classes import stickers

from functions import cachedDbCalls

from globals.globalvars import videoRoot

stickerLocation = os.path.join(videoRoot, "images/stickers/")


@socketio.on("editSticker")
def editSticker(message):
    stickerID = int(message["stickerID"])

    stickerQuery = stickers.stickers.query.filter_by(id=stickerID)
    stickerFolder = stickerLocation

    hasAuthority = False

    if "channelID" in message:
        channelID = int(message["channelID"])
        channelQuery = cachedDbCalls.getChannel(channelID)
        if channelQuery is not None and channelQuery.owningUser == current_user.id:
            hasAuthority = True
            stickerQuery = stickerQuery.filter_by(channelID=channelID)
            stickerFolder = os.path.join(stickerLocation, channelQuery.channelLoc)
    else:
        if current_user.has_role("Admin"):
            hasAuthority = True
            stickerQuery = stickerQuery.filter(stickers.stickers.channelID == None)
    
    if not hasAuthority:
        db.session.close()
        return "Not allowed"

    oldFilename = stickerQuery.with_entities(
        stickers.stickers.filename
    ).scalar()
    if oldFilename is None:
        db.session.close()
        return "Sticker Not Found"

    stickerPath = os.path.join(stickerFolder, oldFilename)
    if not os.path.isfile(stickerPath):
        db.session.close()
        return "Sticker Not Found"

    newName = str(message["newName"])
    newFilename = f"{newName}.{oldFilename.split('.', 1)[1]}"

    try:
        os.rename(
            stickerPath,
            os.path.join(stickerFolder, newFilename)
        )
    except OSError:
        db.session.close()
        return "Failed to edit Sticker"

    stickerQuery.update(dict(name=newName, filename=newFilename))
    db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("deleteSticker")
def deleteSticker(message):
    stickerID = int(message["stickerID"])

    stickerQuery = stickers.stickers.query.filter_by(id=stickerID)
    stickerFolder = stickerLocation

    hasAuthority = False

    if "channelID" in message:
        channelID = int(message["channelID"])
        channelQuery = cachedDbCalls.getChannel(channelID)
        if channelQuery is not None and channelQuery.owningUser == current_user.id:
            hasAuthority = True
            stickerQuery = stickerQuery.filter_by(channelID=channelID)
            stickerFolder = os.path.join(stickerLocation, channelQuery.channelLoc)
    else:
        if current_user.has_role("Admin"):
            hasAuthority = True
            stickerQuery = stickerQuery.filter(stickers.stickers.channelID == None)

    if not hasAuthority:
        db.session.close()
        return "Not allowed"

    stickerFilename = stickerQuery.with_entities(
        stickers.stickers.filename
    ).scalar()
    if stickerFilename is None:
        db.session.close()
        return "Sticker Not Found"

    stickerPath = os.path.join(stickerFolder, stickerFilename)
    if not os.path.isfile(stickerPath):
        db.session.close()
        return "Sticker Not Found"

    try:
        os.remove(stickerPath)
    except OSError:
        db.session.close()
        return "Failed to delete Sticker"
    stickerQuery.delete()
    db.session.commit()
    db.session.close()
    return "OK"
