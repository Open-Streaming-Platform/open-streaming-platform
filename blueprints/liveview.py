from flask import Blueprint, request, url_for, render_template, redirect, flash
from flask_security import current_user, login_required
from sqlalchemy.sql.expression import func
import hashlib

from classes.shared import db
from classes import settings
from classes import RecordedVideo
from classes import subscriptions
from classes import topics
from classes import views
from classes import Channel
from classes import Stream
from classes import Sec
from classes import banList
from classes import stickers
from classes import panel

from globals.globalvars import ejabberdServer, ejabberdServerHttpBindFQDN

from functions import themes
from functions import securityFunc
from functions import cachedDbCalls

liveview_bp = Blueprint('liveview', __name__, url_prefix='/view')

@liveview_bp.route('/<loc>/')
def view_page(loc):
    sysSettings = cachedDbCalls.getSystemSettings()

    xmppserver = sysSettings.siteAddress

    if ejabberdServerHttpBindFQDN != None:
        xmppserver = ejabberdServerHttpBindFQDN
    elif ejabberdServer != "127.0.0.1" and ejabberdServer != "localhost":
        xmppserver = ejabberdServer

    requestedChannel = Channel.Channel.query.filter_by(channelLoc=loc).first()
    if requestedChannel is not None:

        if requestedChannel.private:
            if current_user.is_authenticated:
                if current_user.id != requestedChannel.owningUser and current_user.has_role('Admin') is False:
                    flash("No Such Stream at URL", "error")
                    return redirect(url_for("root.main_page"))
            else:
                flash("No Such Stream at URL", "error")
                return redirect(url_for("root.main_page"))

        if requestedChannel.protected and sysSettings.protectionEnabled:
            if not securityFunc.check_isValidChannelViewer(requestedChannel.id):
                return render_template(themes.checkOverride('channelProtectionAuth.html'))
            # Reload due to detached session during Valid User Check:
            requestedChannel = Channel.Channel.query.filter_by(channelLoc=loc).first()


        # Pull ejabberd Chat Options for Room
        #from app import ejabberd
        #chatOptions = ejabberd.get_room_options(requestedChannel.channelLoc, 'conference.' + sysSettings.siteAddress)
        #for option in chatOptions:
        #    print(option)

        # Generate CSV String for Banned Chat List
        bannedWordQuery = banList.chatBannedWords.query.all()
        bannedWordArray = []
        for bannedWord in bannedWordQuery:
            bannedWordArray.append(bannedWord.word)

        streamData = Stream.Stream.query.filter_by(active=True, streamKey=requestedChannel.streamKey).first()

        # Stream URL Generation
        streamURL = ''
        edgeQuery = settings.edgeStreamer.query.filter_by(active=True).all()
        if sysSettings.proxyFQDN != None:
            if sysSettings.adaptiveStreaming is True:
                streamURL = '/proxy-adapt/' + requestedChannel.channelLoc + '.m3u8'
            else:
                streamURL = '/proxy/' + requestedChannel.channelLoc + '/index.m3u8'
        elif edgeQuery != []:
            # Handle Selecting the Node using Round Robin Logic
            if sysSettings.adaptiveStreaming is True:
                streamURL = '/edge-adapt/' + requestedChannel.channelLoc + '.m3u8'
            else:
                streamURL = '/edge/' + requestedChannel.channelLoc + '/index.m3u8'
        else:
            if sysSettings.adaptiveStreaming is True:
                streamURL = '/live-adapt/' + requestedChannel.channelLoc + '.m3u8'
            else:
                streamURL = '/live/' + requestedChannel.channelLoc + '/index.m3u8'

        topicList = topics.topics.query.all()
        chatOnly = request.args.get("chatOnly")

        # Grab List of Stickers for Chat

        stickerList = []
        stickerSelectorList = {'builtin': [], 'global': [], 'channel': []}

        # Build Built-In Stickers
        builtinStickerList = [
            {'name': 'oe-angry', 'filename': 'angry.png'},
            {'name': 'oe-smiling', 'filename': 'smiling.png'},
            {'name': 'oe-surprised', 'filename': 'surprised.png'},
            {'name': 'oe-cry', 'filename': 'cry.png'},
            {'name': 'oe-frown', 'filename': 'frown.png'},
            {'name': 'oe-laugh', 'filename': 'laugh.png'},
            {'name': 'oe-think', 'filename': 'thinking.png'},
            {'name': 'oe-thumbsup', 'filename': 'thumbsup.png'},
            {'name': 'oe-thumbsdown', 'filename': 'thumbsdown.png'},
            {'name': 'oe-heart', 'filename': 'heart.png'},
            {'name': 'oe-star', 'filename': 'star.png'},
            {'name': 'oe-fire', 'filename': 'fire.png'},
            {'name': 'oe-checkmark', 'filename': 'checkmark.png'}
        ]
        for sticker in builtinStickerList:
            newSticker = {'name': sticker['name'], 'file': '/static/img/stickers/' + sticker['filename'], 'category': 'builtin'}
            stickerList.append(newSticker)
            stickerSelectorList['builtin'].append(newSticker)

        # Build Global Stickers
        stickerQuery = stickers.stickers.query.filter_by(channelID=None).all()
        for sticker in stickerQuery:

            category = 'global'
            stickerFolder = "/images/stickers/"

            newSticker = {'name': sticker.name, 'file': stickerFolder + sticker.filename, 'category': category}
            stickerList.append(newSticker)
            stickerSelectorList[category].append(newSticker)

        # Build Channel Stickers
        stickerQuery = stickers.stickers.query.filter_by(channelID=requestedChannel.id).all()
        for sticker in stickerQuery:

            category = 'channel'
            stickerFolder = "/images/stickers/" + requestedChannel.channelLoc + "/"

            newSticker = {'name': sticker.name, 'file': stickerFolder + sticker.filename, 'category': category}
            stickerList.append(newSticker)
            stickerSelectorList[category].append(newSticker)

        if chatOnly == "True" or chatOnly == "true":
            if requestedChannel.chatEnabled:
                hideBar = False
                hideBarReq = request.args.get("hideBar")
                if hideBarReq == "True" or hideBarReq == "true":
                    hideBar = True

                guestUser = None
                if 'guestUser' in request.args and current_user.is_authenticated is False:
                    guestUser = request.args.get("guestUser")

                    userQuery = Sec.User.query.filter_by(username=guestUser).first()
                    if userQuery is not None:
                        flash("Invalid User","error")
                        return(redirect(url_for("root.main_page")))

                return render_template(themes.checkOverride('chatpopout.html'), stream=streamData, streamURL=streamURL, sysSettings=sysSettings, channel=requestedChannel, hideBar=hideBar, guestUser=guestUser,
                                       xmppserver=xmppserver, stickerList=stickerList, stickerSelectorList=stickerSelectorList, bannedWords=bannedWordArray)
            else:
                flash("Chat is Not Enabled For This Stream","error")

        isEmbedded = request.args.get("embedded")

        #requestedChannel = Channel.Channel.query.filter_by(channelLoc=loc).first()

        if isEmbedded is None or isEmbedded == "False" or isEmbedded == "false":

            secureHash = None
            rtmpURI = None

            endpoint = 'live'

            if requestedChannel.protected:
                if current_user.is_authenticated:
                    secureHash = None
                    if current_user.authType == 0:
                        secureHash = hashlib.sha256((current_user.username + requestedChannel.channelLoc + current_user.password).encode('utf-8')).hexdigest()
                    else:
                        secureHash = hashlib.sha256((current_user.username + requestedChannel.channelLoc + current_user.oAuthID).encode('utf-8')).hexdigest()
                    username = current_user.username
                    rtmpURI = 'rtmp://' + sysSettings.siteAddress + ":1935/" + endpoint + "/" + requestedChannel.channelLoc + "?username=" + username + "&hash=" + secureHash
                else:
                    # TODO Add method for Unauthenticated Guest Users with an invite code to view RTMP
                    rtmpURI = 'rtmp://' + sysSettings.siteAddress + ":1935/" + endpoint + "/" + requestedChannel.channelLoc
            else:
                rtmpURI = 'rtmp://' + sysSettings.siteAddress + ":1935/" + endpoint + "/" + requestedChannel.channelLoc

            clipsList = []
            for vid in requestedChannel.recordedVideo:
                for clip in vid.clips:
                    if clip.published is True:
                        clipsList.append(clip)
            clipsList.sort(key=lambda x: x.views, reverse=True)

            subState = False
            if current_user.is_authenticated:
                chanSubQuery = subscriptions.channelSubs.query.filter_by(channelID=requestedChannel.id, userID=current_user.id).first()
                if chanSubQuery is not None:
                    subState = True

            channelPanelList = panel.panelMapping.query.filter_by(pageName="liveview.view_page", panelType=2, panelLocationId=requestedChannel.id).all()
            channelPanelListSorted = sorted(channelPanelList, key=lambda x: x.panelOrder)

            return render_template(themes.checkOverride('channelplayer.html'), stream=streamData, streamURL=streamURL, topics=topicList, channel=requestedChannel, clipsList=clipsList,
                                   subState=subState, secureHash=secureHash, rtmpURI=rtmpURI, xmppserver=xmppserver, stickerList=stickerList, stickerSelectorList=stickerSelectorList,
                                   bannedWords=bannedWordArray, channelPanelList=channelPanelListSorted)
        else:
            isAutoPlay = request.args.get("autoplay")
            if isAutoPlay is None:
                isAutoPlay = False
            elif isAutoPlay.lower() == 'true':
                isAutoPlay = True
            else:
                isAutoPlay = False

            countViewers = request.args.get("countViewers")
            if countViewers is None:
                countViewers = True
            elif countViewers.lower() == 'false':
                countViewers = False
            else:
                countViewers = False
            return render_template(themes.checkOverride('channelplayer_embed.html'), channel=requestedChannel, stream=streamData, streamURL=streamURL, topics=topicList, isAutoPlay=isAutoPlay, countViewers=countViewers, xmppserver=xmppserver)

    else:
        flash("No Live Stream at URL","error")
        return redirect(url_for("root.main_page"))