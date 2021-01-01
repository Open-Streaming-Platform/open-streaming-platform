from flask import Blueprint, request, url_for, render_template, redirect, flash
from flask_security import current_user, login_required
from sqlalchemy.sql.expression import func
from os import path

from classes.shared import db
from classes import settings
from classes import RecordedVideo
from classes import subscriptions
from classes import topics
from classes import views
from classes import comments
from classes import notifications
from classes import upvotes

from functions import themes
from functions import system
from functions import videoFunc
from functions import securityFunc
from functions import webhookFunc
from functions import templateFilters

from globals import globalvars

play_bp = Blueprint('play', __name__, url_prefix='/play')

@play_bp.route('/<videoID>')
def view_vid_page(videoID):
    sysSettings = settings.settings.query.first()
    videos_root = globalvars.videoRoot + 'videos/'

    recordedVid = RecordedVideo.RecordedVideo.query.filter_by(id=videoID).first()

    if recordedVid is not None:

        if recordedVid.published is False:
            if current_user.is_authenticated:
                if current_user != recordedVid.owningUser and current_user.has_role('Admin') is False:
                    flash("No Such Video at URL", "error")
                    return redirect(url_for("root.main_page"))
            else:
                flash("No Such Video at URL", "error")
                return redirect(url_for("root.main_page"))

        if recordedVid.channel.protected and sysSettings.protectionEnabled:
            if not securityFunc.check_isValidChannelViewer(recordedVid.channel.id):
                return render_template(themes.checkOverride('channelProtectionAuth.html'))

        # Check if the file exists in location yet and redirect if not ready
        if path.exists(videos_root + recordedVid.videoLocation) is False:
            return render_template(themes.checkOverride('notready.html'), video=recordedVid)

        # Check if the DB entry for the video has a length, if not try to determine or fail
        if recordedVid.length is None:
            fullVidPath = videos_root + recordedVid.videoLocation
            duration = None
            try:
                duration = videoFunc.getVidLength(fullVidPath)
            except:
                return render_template(themes.checkOverride('notready.html'), video=recordedVid)
            recordedVid.length = duration
        db.session.commit()

        recordedVid.views = recordedVid.views + 1
        recordedVid.channel.views = recordedVid.channel.views + 1

        topicList = topics.topics.query.all()

        streamURL = '/videos/' + recordedVid.videoLocation

        isEmbedded = request.args.get("embedded")

        newView = views.views(1, recordedVid.id)
        db.session.add(newView)
        db.session.commit()

        # Function to allow custom start time on Video
        startTime = None
        if 'startTime' in request.args:
            startTime = request.args.get("startTime")
        try:
            startTime = float(startTime)
        except:
            startTime = None

        if isEmbedded is None or isEmbedded == "False":

            randomRecorded = RecordedVideo.RecordedVideo.query.filter(RecordedVideo.RecordedVideo.pending == False, RecordedVideo.RecordedVideo.id != recordedVid.id, RecordedVideo.RecordedVideo.published == True).order_by(func.random()).limit(12)

            subState = False
            if current_user.is_authenticated:
                chanSubQuery = subscriptions.channelSubs.query.filter_by(channelID=recordedVid.channel.id, userID=current_user.id).first()
                if chanSubQuery is not None:
                    subState = True

            return render_template(themes.checkOverride('vidplayer.html'), video=recordedVid, streamURL=streamURL, topics=topicList, randomRecorded=randomRecorded, subState=subState, startTime=startTime)
        else:
            isAutoPlay = request.args.get("autoplay")
            if isAutoPlay is None:
                isAutoPlay = False
            elif isAutoPlay.lower() == 'true':
                isAutoPlay = True
            else:
                isAutoPlay = False
            return render_template(themes.checkOverride('vidplayer_embed.html'), video=recordedVid, streamURL=streamURL, topics=topicList, isAutoPlay=isAutoPlay, startTime=startTime)
    else:
        flash("No Such Video at URL","error")
        return redirect(url_for("root.main_page"))

@play_bp.route('/<videoID>/clip', methods=['POST'])
@login_required
def vid_clip_page(videoID):

    clipStart = float(request.form['clipStartTime'])
    clipStop = float(request.form['clipStopTime'])
    clipName = str(request.form['clipName'])
    clipDescription = str(request.form['clipDescription'])

    result = videoFunc.createClip(videoID, clipStart, clipStop, clipName, clipDescription)

    if result[0] is True:
        flash("Clip Created", "success")
        return redirect(url_for("clip.view_clip_page", clipID=result[1]))
    else:
        flash("Unable to create Clip", "error")
        return redirect(url_for(".view_vid_page", videoID=videoID))

@play_bp.route('/<videoID>/move', methods=['POST'])
@login_required
def vid_move_page(videoID):

    videoID = videoID
    newChannel = int(request.form['moveToChannelID'])

    result = videoFunc.moveVideo(videoID, newChannel)
    if result is True:
        flash("Video Moved to Another Channel", "success")
        return redirect(url_for('.view_vid_page', videoID=videoID))
    else:
        flash("Error Moving Video", "error")
        return redirect(url_for("root.main_page"))

@play_bp.route('/<videoID>/change', methods=['POST'])
@login_required
def vid_change_page(videoID):

    newVideoName = system.strip_html(request.form['newVidName'])
    newVideoTopic = request.form['newVidTopic']
    description = request.form['description']

    allowComments = False
    if 'allowComments' in request.form:
        allowComments = True

    result = videoFunc.changeVideoMetadata(videoID, newVideoName, newVideoTopic, description, allowComments)

    if result is True:
        flash("Changed Video Metadata", "success")
        return redirect(url_for('.view_vid_page', videoID=videoID))
    else:
        flash("Error Changing Video Metadata", "error")
        return redirect(url_for("root.main_page"))

@play_bp.route('/<videoID>/delete')
@login_required
def delete_vid_page(videoID):

    result = videoFunc.deleteVideo(videoID)

    if result is True:
        flash("Video deleted")
        return redirect(url_for('root.main_page'))
    else:
        flash("Error Deleting Video")
        return redirect(url_for('.view_vid_page', videoID=videoID))

@play_bp.route('/<videoID>/comment', methods=['GET','POST'])
@login_required
def comments_vid_page(videoID):
    sysSettings = settings.settings.query.first()

    recordedVid = RecordedVideo.RecordedVideo.query.filter_by(id=videoID).first()

    if recordedVid is not None:

        if request.method == 'POST':

            comment = system.strip_html(request.form['commentText'])
            currentUser = current_user.id

            newComment = comments.videoComments(currentUser,comment,recordedVid.id)
            db.session.add(newComment)
            db.session.commit()

            if recordedVid.channel.imageLocation is None:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
            else:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + recordedVid.channel.imageLocation)

            pictureLocation = ""
            if current_user.pictureLocation is None:
                pictureLocation = '/static/img/user2.png'
            else:
                pictureLocation = '/images/' + pictureLocation

            newNotification = notifications.userNotification(templateFilters.get_userName(current_user.id) + " commented on your video - " + recordedVid.channelName, '/play/' + str(recordedVid.id),
                                                                 "/images/" + str(current_user.pictureLocation), recordedVid.owningUser)
            db.session.add(newNotification)
            db.session.commit()

            webhookFunc.runWebhook(recordedVid.channel.id, 7, channelname=recordedVid.channel.channelName,
                       channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(recordedVid.channel.id)),
                       channeltopic=templateFilters.get_topicName(recordedVid.channel.topic),
                       channelimage=channelImage, streamer=templateFilters.get_userName(recordedVid.channel.owningUser),
                       channeldescription=str(recordedVid.channel.description), videoname=recordedVid.channelName,
                       videodate=recordedVid.videoDate, videodescription=recordedVid.description,
                       videotopic=templateFilters.get_topicName(recordedVid.topic),
                       videourl=(sysSettings.siteProtocol + sysSettings.siteAddress + '/videos/' + recordedVid.videoLocation),
                       videothumbnail=(sysSettings.siteProtocol + sysSettings.siteAddress + '/videos/' + recordedVid.thumbnailLocation),
                       user=current_user.username, userpicture=(sysSettings.siteProtocol + sysSettings.siteAddress + str(pictureLocation)), comment=comment)
            flash('Comment Added', "success")
            system.newLog(4, "Video Comment Added by " + current_user.username + "to Video ID #" + str(recordedVid.id))

        elif request.method == 'GET':
            if request.args.get('action') == "delete":
                commentID = int(request.args.get('commentID'))
                commentQuery = comments.videoComments.query.filter_by(id=commentID).first()
                if commentQuery is not None:
                    if current_user.has_role('Admin') or recordedVid.owningUser == current_user.id or commentQuery.userID == current_user.id:
                        upvoteQuery = upvotes.commentUpvotes.query.filter_by(commentID=commentQuery.id).all()
                        for vote in upvoteQuery:
                            db.session.delete(vote)
                        db.session.delete(commentQuery)
                        db.session.commit()
                        system.newLog(4, "Video Comment Deleted by " + current_user.username + "to Video ID #" + str(recordedVid.id))
                        flash('Comment Deleted', "success")
                    else:
                        flash("Not Authorized to Remove Comment", "error")

    else:
        flash('Invalid Video ID','error')
        return redirect(url_for('root.main_page'))

    return redirect(url_for('.view_vid_page', videoID=videoID))