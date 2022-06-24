import sys
from os import path, remove

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from flask import Blueprint, request, url_for, render_template, redirect, flash

from classes.shared import db
from classes import settings
from classes import Channel
from classes import RecordedVideo
from classes import Stream
from classes import Sec

from functions import themes
from functions import cachedDbCalls

streamers_bp = Blueprint("streamers", __name__, url_prefix="/streamer")


@streamers_bp.route("/")
def streamers_page():
    sysSettings = cachedDbCalls.getSystemSettings()
    streamerIDs = []

    if sysSettings.showEmptyTables:
        for channel in db.session.query(Channel.Channel.owningUser).distinct():
            if channel.owningUser not in streamerIDs:
                streamerIDs.append(channel.owningUser)
    else:
        openStreams = Stream.Stream.query.filter_by(active=True).all()
        for stream in openStreams:
            if stream.channel.owningUser not in streamerIDs:
                streamerIDs.append(stream.channel.owningUser)
        for recordedVidInstance in db.session.query(
            RecordedVideo.RecordedVideo.owningUser
        ).distinct():
            if recordedVidInstance.owningUser not in streamerIDs:
                streamerIDs.append(recordedVidInstance.owningUser)

    streamerList = []
    for userID in streamerIDs:
        userQuery = Sec.User.query.filter_by(id=userID).first()
        if userQuery is not None:
            streamerList.append(userQuery)

    return render_template(
        themes.checkOverride("streamers.html"), streamerList=streamerList
    )


@streamers_bp.route("/<userID>/")
def streamers_view_page(userID):
    userID = int(userID)

    streamerQuery = Sec.User.query.filter_by(id=userID).first()
    if streamerQuery is not None:
        if streamerQuery.has_role("Streamer"):
            userChannels = cachedDbCalls.getChannelsByOwnerId(userID)
            channelIds = []
            for channel in userChannels:
                channelIds.append(channel.id)

            streams = (
                Stream.Stream.query.filter(
                    Stream.Stream.active == True,
                    Stream.Stream.linkedChannel.in_(channelIds),
                )
                .with_entities(
                    Stream.Stream.id,
                    Stream.Stream.linkedChannel,
                    Stream.Stream.currentViewers,
                    Stream.Stream.topic,
                    Stream.Stream.streamName,
                    Stream.Stream.totalViewers,
                    Stream.Stream.startTimestamp,
                    Stream.Stream.uuid,
                    Stream.Stream.active,
                )
                .all()
            )

            recordedVideoQuery = cachedDbCalls.getAllVideoByOwnerId(userID)

            # Sort Video to Show Newest First
            recordedVideoQuery.sort(key=lambda x: x.videoDate, reverse=True)

            clipsList = cachedDbCalls.getAllClipsForUser(userID)

            clipsList.sort(key=lambda x: x.views, reverse=True)

            return render_template(
                themes.checkOverride("videoListView.html"),
                openStreams=streams,
                recordedVids=recordedVideoQuery,
                userChannels=userChannels,
                clipsList=clipsList,
                title=streamerQuery.username,
                streamerData=streamerQuery,
            )
    flash("Invalid Streamer", "error")
    return redirect(url_for("root.main_page"))
