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
from classes import Channel
from classes.shared import cache

from functions import themes
from functions import system
from functions import videoFunc
from functions import securityFunc
from functions import webhookFunc
from functions import templateFilters
from functions import cachedDbCalls
from functions.scheduled_tasks import video_tasks, message_tasks

from globals import globalvars

play_bp = Blueprint('play', __name__, url_prefix='/play')

@play_bp.route('/<videoID>')
def view_vid_page(videoID):
    sysSettings = cachedDbCalls.getSystemSettings()
    videos_root = globalvars.videoRoot + 'videos/'

    recordedVid = cachedDbCalls.getVideo(videoID)

    if recordedVid is not None:
        channelData = cachedDbCalls.getChannel(recordedVid.channelID)

        if recordedVid.published is False:
            if current_user.is_authenticated:
                if current_user != recordedVid.owningUser and current_user.has_role('Admin') is False:
                    flash("No Such Video at URL", "error")
                    return redirect(url_for("root.main_page"))
            else:
                flash("No Such Video at URL", "error")
                return redirect(url_for("root.main_page"))

        if channelData.private:
            if current_user.is_authenticated:
                if current_user.id != channelData.owningUser and current_user.has_role('Admin') is False:
                    flash("No Such Channel", "error")
                    return redirect(url_for("root.main_page"))
            else:
                flash("No Such Channel", "error")
                return redirect(url_for("root.main_page"))

        if channelData.protected and sysSettings.protectionEnabled:
            if not securityFunc.check_isValidChannelViewer(channelData.id):
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
            RecordedVideo.RecordedVideo.query.filter_by(id=recordedVid.id).update(dict(length=duration))
        db.session.commit()

        RecordedVideo.RecordedVideo.query.filter_by(id=recordedVid.id).update(dict(views=recordedVid.views + 1))

        Channel.Channel.query.filter_by(id=recordedVid.channelID).update(dict(views=channelData.views + 1))

        topicList = cachedDbCalls.getAllTopics()

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

            randomRecorded = RecordedVideo.RecordedVideo.query.filter(
                RecordedVideo.RecordedVideo.pending is False, RecordedVideo.RecordedVideo.id != recordedVid.id, RecordedVideo.RecordedVideo.published is True)\
                .order_by(func.random()).limit(12)

            subState = False
            if current_user.is_authenticated:
                chanSubQuery = subscriptions.channelSubs.query.filter_by(channelID=channelData.id, userID=current_user.id).first()
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

    videoQuery = cachedDbCalls.getVideo(videoID)
    if videoQuery.owningUser == current_user.id:
        result = video_tasks.create_video_clip.delay(videoID, clipStart, clipStop, clipName, clipDescription)
        flash("Clip Queued for Creation", "success")
    else:
        flash("Current Video Owner is not current owner","error")
    return redirect(url_for(".view_vid_page", videoID=videoID))

@play_bp.route('/<videoID>/move', methods=['POST'])
@login_required
def vid_move_page(videoID):

    videoID = videoID
    newChannel = int(request.form['moveToChannelID'])

    result = videoFunc.moveVideo(videoID, newChannel)
    if result is True:
        cache.delete_memoized(cachedDbCalls.getVideo, videoID)
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

    videoQuery = cachedDbCalls.getVideo(videoID)

    if videoQuery.owningUser == current_user.id:

        if 'videoTags' in request.form:
            videoTagString = request.form['videoTags']
            tagArray = system.parseTags(videoTagString)
            existingTagArray = RecordedVideo.video_tags.query.filter_by(videoID=videoID).all()

            for currentTag in existingTagArray:
                if currentTag.name not in tagArray:
                    db.session.delete(currentTag)
                else:
                    tagArray.remove(currentTag.name)
            db.session.commit()
            for currentTag in tagArray:
                newTag = RecordedVideo.video_tags(currentTag, videoID, current_user.id)
                db.session.add(newTag)
                db.session.commit()

        allowComments = False
        if 'allowComments' in request.form:
            allowComments = True

        result = videoFunc.changeVideoMetadata(videoID, newVideoName, newVideoTopic, description, allowComments)
        cache.delete_memoized(cachedDbCalls.getVideo, videoID)

        if result is True:
            flash("Changed Video Metadata", "success")
            return redirect(url_for('.view_vid_page', videoID=videoID))
        else:
            flash("Error Changing Video Metadata", "error")
            return redirect(url_for("root.main_page"))
    else:
        flash("No Access to edit video metadata", "error")
        return redirect(url_for('.view_vid_page', videoID=videoID))

@play_bp.route('/<videoID>/delete')
@login_required
def delete_vid_page(videoID):
    videoQuery = cachedDbCalls.getVideo(videoID)
    if videoQuery.owningUser == current_user.id:
        result = video_tasks.delete_video.delay(videoID)

        cache.delete_memoized(cachedDbCalls.getVideo, videoID)
        flash("Video Scheduled for Deletion", "success")
        return redirect(url_for('root.main_page'))
    else:
        flash("Error Deleting Video")
        return redirect(url_for('.view_vid_page', videoID=videoID))

@play_bp.route('/<videoID>/comment', methods=['GET','POST'])
@login_required
def comments_vid_page(videoID):
    sysSettings = cachedDbCalls.getSystemSettings()

    #recordedVid = RecordedVideo.RecordedVideo.query.filter_by(id=videoID).first()
    recordedVid = cachedDbCalls.getVideo(videoID)

    if recordedVid is not None:

        if request.method == 'POST':

            comment = system.strip_html(request.form['commentText'])
            currentUser = current_user.id

            newComment = comments.videoComments(currentUser,comment,recordedVid.id)
            db.session.add(newComment)
            db.session.commit()

            channelQuery = cachedDbCalls.getChannel(recordedVid.channelID)
            if channelQuery.imageLocation is None:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
            else:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + channelQuery.imageLocation)

            pictureLocation = ""
            if current_user.pictureLocation is None:
                pictureLocation = '/static/img/user2.png'
            else:
                pictureLocation = '/images/' + pictureLocation

            newNotification = notifications.userNotification(templateFilters.get_userName(current_user.id) + " commented on your video - " + recordedVid.channelName, '/play/' + str(recordedVid.id),
                                                                 "/images/" + str(current_user.pictureLocation), recordedVid.owningUser)
            db.session.add(newNotification)
            db.session.commit()

            message_tasks.send_webhook.delay(channelQuery.id, 7, channelname=channelQuery.channelName,
                       channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(channelQuery.id)),
                       channeltopic=templateFilters.get_topicName(channelQuery.topic),
                       channelimage=channelImage, streamer=templateFilters.get_userName(channelQuery.owningUser),
                       channeldescription=str(channelQuery.description), videoname=recordedVid.channelName,
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