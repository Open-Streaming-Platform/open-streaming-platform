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

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/<username>")
def profile_view_page(username):

    userQuery = Sec.User.query.filter_by(username=username).first()
    if userQuery is not None:
        userChannels = Channel.Channel.query.filter_by(owningUser=userQuery.id).all()

        streams = []

        for channel in userChannels:
            for stream in channel.stream:
                if stream.active is True:
                    streams.append(stream)

        recordedVideoQuery = RecordedVideo.RecordedVideo.query.filter_by(
            owningUser=userQuery.id, pending=False, published=True
        ).all()

        # Sort Video to Show Newest First
        recordedVideoQuery.sort(key=lambda x: x.videoDate, reverse=True)

        clipsList = []
        for vid in recordedVideoQuery:
            for clip in vid.clips:
                if clip.published is True:
                    clipsList.append(clip)

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
