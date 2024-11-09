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

from functions import themes, cachedDbCalls

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/<username>")
def profile_view_page(username):

    userQuery = Sec.User.query.filter_by(username=username).first()
    if userQuery is not None:
        userChannels = cachedDbCalls.getChannelsByOwnerId(userQuery.id)

        streams = []

        for channel in userChannels:
            activeStreams = (
                Stream.Stream.query.filter_by(active=True, linkedChannel=channel.id)
                    .with_entities(
                    Stream.Stream.streamName,
                    Stream.Stream.linkedChannel,
                    Stream.Stream.currentViewers,
                    Stream.Stream.topic,
                    Stream.Stream.id,
                    Stream.Stream.uuid,
                    Stream.Stream.startTimestamp,
                    Stream.Stream.totalViewers,
                    Stream.Stream.active,
                )
                    .order_by(Stream.Stream.currentViewers)
                    .all()
            )
            for stream in activeStreams:
                streams.append(stream)

        recordedVideoQuery = cachedDbCalls.getAllVideoByOwnerId(userQuery.id)

        # Sort Video to Show Newest First
        recordedVideoQuery.sort(key=lambda x: x.videoDate, reverse=True)

        clipsList = RecordedVideo.Clips.query.filter_by(
            published=True, owningUser=userQuery.id
        ).join(
            Channel.Channel,
            Channel.Channel.id == RecordedVideo.Clips.channelID,
        ).join(
            Sec.User, Sec.User.id == RecordedVideo.Clips.owningUser
        ).with_entities(
            RecordedVideo.Clips.id,
            RecordedVideo.Clips.thumbnailLocation,
            RecordedVideo.Clips.owningUser,
            RecordedVideo.Clips.views,
            RecordedVideo.Clips.length,
            RecordedVideo.Clips.clipName,
            Channel.Channel.protected,
            RecordedVideo.Clips.channelID,
            Channel.Channel.channelName,
            RecordedVideo.Clips.topic,
            RecordedVideo.Clips.clipDate,
            Sec.User.pictureLocation,
            RecordedVideo.Clips.parentVideo,
        ).all()

        clipsList.sort(key=lambda x: x.views, reverse=True)

        return render_template(
            themes.checkOverride("videoListView.html"),
            openStreams=streams,
            recordedVids=recordedVideoQuery,
            userChannels=userChannels,
            clipsList=clipsList,
            title=userQuery.username,
            streamerData=userQuery,
        )
    flash("Invalid User", "error")
    return redirect(url_for("root.main_page"))
