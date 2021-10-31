import os
import shutil
import logging

from flask_security import current_user

from globals import globalvars

from classes.shared import db
from classes import Channel

from functions import videoFunc
from functions import cachedDbCalls
from functions import system

def delete_channel(channelID):

    channelQuery = Channel.Channel.query.filter_by(id=channelID).first()
    if channelQuery is not None:
        for vid in channelQuery.recordedVideo:
            videoFunc.deleteVideo(vid.id)

        for upvote in channelQuery.upvotes:
            db.session.delete(upvote)
        for inviteCode in channelQuery.inviteCodes:
            db.session.delete(inviteCode)
        for viewer in channelQuery.invitedViewers:
            db.session.delete(viewer)
        for sub in channelQuery.subscriptions:
            db.session.delete(sub)
        for hook in channelQuery.webhooks:
            db.session.delete(hook)
        for sticker in channelQuery.chatStickers:
            db.session.delete(sticker)

        stickerFolder = '/var/www/images/stickers/' + channelQuery.channelLoc + '/'
        shutil.rmtree(stickerFolder, ignore_errors=True)

        filePath = globalvars.videoRoot + channelQuery.channelLoc

        if filePath != globalvars.videoRoot:
            shutil.rmtree(filePath, ignore_errors=True)

        from app import ejabberd

        sysSettings = cachedDbCalls.getSystemSettings()
        ejabberd.destroy_room(channelQuery.channelLoc, 'conference.' + sysSettings.siteAddress)

        system.newLog(1, "User " + current_user.username + " deleted Channel " + str(channelQuery.id))
        db.session.delete(channelQuery)
        db.session.commit()
    db.session.close()
    return True