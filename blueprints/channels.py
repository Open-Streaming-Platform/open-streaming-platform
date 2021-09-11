from flask import Blueprint, request, url_for, render_template, redirect, flash
from flask_security import current_user

from classes import settings
from classes import Channel
from classes import RecordedVideo
from classes import Stream
from classes import subscriptions

from functions import themes
from functions import cachedDbCalls

channels_bp = Blueprint('channel', __name__, url_prefix='/channel')

@channels_bp.route('/')
def channels_page():
    sysSettings = cachedDbCalls.getSystemSettings()

    channelList = cachedDbCalls.getAllChannels()

    if sysSettings.showEmptyTables is False:
        channelListArray = []
        for channel in channelList:
            chanVidQuery = cachedDbCalls.getChannelVideos(channel.id)
            if len(chanVidQuery) > 0:
                channelListArray.append(channel)
        channelList = channelListArray
    return render_template(themes.checkOverride('channels.html'), channelList=channelList)

@channels_bp.route('/<int:chanID>/')
def channel_view_page(chanID):
    chanID = int(chanID)

    #channelData = Channel.Channel.query.filter_by(id=chanID).first()
    channelData = cachedDbCalls.getChannel(chanID)

    if channelData is not None:

        openStreams = Stream.Stream.query.filter_by(linkedChannel=chanID).all()

        recordedVids = cachedDbCalls.getAllVideo_View(chanID)

        # Sort Video to Show Newest First
        recordedVids.sort(key=lambda x: x.videoDate, reverse=True)

        clipsList = cachedDbCalls.getAllClipsForChannel_View(channelData.id)
        clipsList.sort(key=lambda x: x.views, reverse=True)

        subState = False
        if current_user.is_authenticated:
            chanSubQuery = subscriptions.channelSubs.query.filter_by(channelID=channelData.id, userID=current_user.id).first()
            if chanSubQuery is not None:
                subState = True

        return render_template(themes.checkOverride('videoListView.html'), channelData=channelData, openStreams=openStreams, recordedVids=recordedVids, clipsList=clipsList, subState=subState, title="Channels - Videos")
    else:
        flash("No Such Channel", "error")
        return redirect(url_for("root.main_page"))

@channels_bp.route('/link/<channelLoc>/')
def channel_view_link_page(channelLoc):
    if channelLoc is not None:
        channelQuery = Channel.Channel.query.filter_by(channelLoc=str(channelLoc)).first()
        if channelQuery is not None:
            return redirect(url_for(".channel_view_page",chanID=channelQuery.id))
    flash("Invalid Channel Location", "error")
    return redirect(url_for("root.main_page"))

# Allow a direct link to any open stream for a channel
@channels_bp.route('/<loc>/stream')
def channel_stream_link_page(loc):
    requestedChannel = Channel.Channel.query.filter_by(id=int(loc)).first()
    if requestedChannel is not None:
        openStreamQuery = Stream.Stream.query.filter_by(linkedChannel=requestedChannel.id).first()
        if openStreamQuery is not None:
            return redirect(url_for("view_page", loc=requestedChannel.channelLoc))
        else:
            flash("No Active Streams for the Channel","error")
            return redirect(url_for(".channel_view_page",chanID=requestedChannel.id))
    else:
        flash("Unknown Channel","error")
        return redirect(url_for("root.main_page"))