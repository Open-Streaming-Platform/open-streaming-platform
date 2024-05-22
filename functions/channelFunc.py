import os
import shutil
import logging

from flask_security import current_user
from flask_socketio import emit

from classes.shared import db, socketio

from globals import globalvars

from classes.shared import db
from classes import Channel
from classes import panel
from classes import banList

from functions import videoFunc
from functions import cachedDbCalls
from functions import system

log = logging.getLogger("app.functions.channelFunctions")

def delete_channel(channelID):

    channelQuery = Channel.Channel.query.filter_by(id=channelID).first()
    if channelQuery is None:
        db.session.close()
        return False

    try:
        panelMappingQuery = panel.panelMapping.query.filter_by(
            panelType=2, panelLocationId=channelQuery.id
        ).all()
        for map in panelMappingQuery:
            db.session.delete(map)

        channelPanelQuery = panel.channelPanel.query.filter_by(
            channelId=channelQuery.id
        ).all()
        for pan in channelPanelQuery:
            db.session.delete(pan)

        globalPanelQuery = panel.globalPanel.query.filter_by(
            type=6, target=channelQuery.id
        ).all()
        for globalpan in globalPanelQuery:
            db.session.delete(globalpan)

        bannedChatMessagesQuery = banList.chatBannedMessages.query.filter_by(
            channelLoc=channelQuery.channelLoc
        ).all()
        for message in bannedChatMessagesQuery:
            db.session.delete(message)

        bannedUsersQuery = banList.channelBanList.query.filter_by(
            channelLoc=channelQuery.channelLoc
        ).all()
        for user in bannedUsersQuery:
            db.session.delete(user)

        for clip in channelQuery.clips:
            videoFunc.deleteClip(clip.id)

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

        stickerFolder = os.path.join(globalvars.videoRoot, "images/stickers", channelQuery.channelLoc)
        if os.path.exists(stickerFolder):
            shutil.rmtree(stickerFolder)

        videosFolder = os.path.join(globalvars.videoRoot, "videos", channelQuery.channelLoc)
        if videosFolder != globalvars.videoRoot and os.path.exists(videosFolder):
            shutil.rmtree(videosFolder)

        from app import ejabberd

        ejabberd.destroy_room(
            channelQuery.channelLoc, "conference." + globalvars.defaultChatDomain
        )

        system.newLog(
            1,
            "User "
            + current_user.username
            + " deleted Channel "
            + str(channelQuery.id),
        )

        cachedDbCalls.invalidateChannelCache(channelQuery.id)

        db.session.delete(channelQuery)
        db.session.commit()
    except Exception as e:
        log.error("Error in deleting Channel " + str(channelQuery.id) + ": " + str(e))
        db.session.close()
        return False

    db.session.close()
    return True

def broadcastEventStream(channelLoc, message):
    emit('eventStream', { 'message': message }, namespace="ES_" + channelLoc, broadcast=True)
