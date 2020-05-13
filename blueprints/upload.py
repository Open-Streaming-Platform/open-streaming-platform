import os
import datetime
import subprocess
import shutil

from flask import Blueprint, request, url_for, render_template, redirect, flash, current_app
from flask_security import current_user, login_required, roles_required
from werkzeug.utils import secure_filename

from classes.shared import db
from classes import settings
from classes import Channel
from classes import RecordedVideo
from classes import subscriptions
from classes import notifications

from functions import system
from functions import webhookFunc
from functions import templateFilters
from functions import subsFunc

from globals import globalvars

upload_bp = Blueprint('upload', __name__, url_prefix='/upload')

@upload_bp.route('/video-files', methods=['GET', 'POST'])
@login_required
@roles_required('Uploader')
def upload():
    videos_root = globalvars.videoRoot + 'videos/'

    sysSettings = settings.settings.query.first()
    if not sysSettings.allowUploads:
        db.session.close()
        return "Video Uploads Disabled", 501
    if request.files['file']:

        if not os.path.exists(videos_root + 'temp'):
            os.makedirs(videos_root + 'temp')

        file = request.files['file']

        if request.form['ospfilename'] != "":
            ospfilename = request.form['ospfilename']
        else:
            return "Ooops.", 500

        if system.videoupload_allowedExt(file.filename, current_app.config['VIDEO_UPLOAD_EXTENSIONS']):
            save_path = os.path.join(current_app.config['VIDEO_UPLOAD_TEMPFOLDER'], secure_filename(ospfilename))
            current_chunk = int(request.form['dzchunkindex'])
        else:
            system.newLog(4,"File Upload Failed - File Type not Allowed - Username:" + current_user.username)
            return "Filetype not allowed", 403

        if current_chunk > 4500:
            open(save_path, 'w').close()
            return "File is getting too large.", 403

        if os.path.exists(save_path) and current_chunk == 0:
            open(save_path, 'w').close()

        try:
            with open(save_path, 'ab') as f:
                f.seek(int(request.form['dzchunkbyteoffset']))
                f.write(file.stream.read())
        except OSError:
            system.newLog(4, "File Upload Failed - OSError - Username:" + current_user.username)
            return "Ooops.", 500

        total_chunks = int(request.form['dztotalchunkcount'])

        if current_chunk + 1 == total_chunks:
            if os.path.getsize(save_path) != int(request.form['dztotalfilesize']):
                return "Size mismatch", 500

        return "success", 200
    else:
        return "I don't understand", 501

@upload_bp.route('/video-details', methods=['POST'])
@login_required
@roles_required('Uploader')
def upload_vid():
    sysSettings = settings.settings.query.first()
    if not sysSettings.allowUploads:
        db.session.close()
        flash("Video Upload Disabled", "error")
        return redirect(url_for('root.main_page'))

    currentTime = datetime.datetime.now()

    channel = int(request.form['uploadToChannelID'])
    topic = int(request.form['uploadTopic'])
    thumbnailFilename = request.form['thumbnailFilename']
    videoFilename= request.form['videoFilename']

    ChannelQuery = Channel.Channel.query.filter_by(id=channel).first()

    if ChannelQuery.owningUser != current_user.id:
        flash('You are not allowed to upload to this channel!')
        db.session.close()
        return redirect(url_for('root.main_page'))

    videoPublishState = ChannelQuery.autoPublish

    newVideo = RecordedVideo.RecordedVideo(current_user.id, channel, ChannelQuery.channelName, ChannelQuery.topic, 0, "", currentTime, ChannelQuery.allowComments, videoPublishState)

    videoLoc = ChannelQuery.channelLoc + "/" + videoFilename.rsplit(".", 1)[0] + '_' + datetime.datetime.strftime(currentTime, '%Y%m%d_%H%M%S') + ".mp4"
    videos_root = current_app.config['WEB_ROOT'] + 'videos/'
    videoPath = videos_root + videoLoc

    if videoFilename != "":
        if not os.path.isdir(videos_root + ChannelQuery.channelLoc):
            try:
                os.mkdir(videos_root + ChannelQuery.channelLoc)
            except OSError:
                system.newLog(4, "File Upload Failed - OSError - Unable to Create Directory - Username:" + current_user.username)
                flash("Error uploading video - Unable to create directory","error")
                db.session.close()
                return redirect(url_for("root.main_page"))
        shutil.move(current_app.config['VIDEO_UPLOAD_TEMPFOLDER'] + '/' + videoFilename, videoPath)
    else:
        db.session.close()
        flash("Error uploading video - Couldn't move video file")
        return redirect(url_for('root.main_page'))

    newVideo.videoLocation = videoLoc

    if thumbnailFilename != "":
        thumbnailLoc = ChannelQuery.channelLoc + '/' + thumbnailFilename.rsplit(".", 1)[0] + '_' +  datetime.datetime.strftime(currentTime, '%Y%m%d_%H%M%S') + videoFilename.rsplit(".", 1)[-1]

        thumbnailPath = videos_root + thumbnailLoc
        try:
            shutil.move(current_app.config['VIDEO_UPLOAD_TEMPFOLDER'] + '/' + thumbnailFilename, thumbnailPath)
        except:
            flash("Thumbnail Upload Failed Due to Missing File","error")
        newVideo.thumbnailLocation = thumbnailLoc
    else:
        thumbnailLoc = ChannelQuery.channelLoc + '/' + videoFilename.rsplit(".", 1)[0] + '_' +  datetime.datetime.strftime(currentTime, '%Y%m%d_%H%M%S') + videoFilename.rsplit(".", 1)[-1]

        subprocess.call(['ffmpeg', '-ss', '00:00:01', '-i', videos_root + videoLoc, '-s', '384x216', '-vframes', '1', videos_root + thumbnailLoc])
        newVideo.thumbnailLocation = thumbnailLoc

    newGifFullThumbnailLocation = ChannelQuery.channelLoc + '/' + videoFilename.rsplit(".", 1)[0] + '_' + datetime.datetime.strftime(currentTime, '%Y%m%d_%H%M%S') + ".gif"
    gifresult = subprocess.call(['ffmpeg', '-ss', '00:00:01', '-t', '3', '-i', videos_root + videoLoc, '-filter_complex', '[0:v] fps=30,scale=w=384:h=-1,split [a][b];[a] palettegen=stats_mode=single [p];[b][p] paletteuse=new=1', '-y', videos_root + newGifFullThumbnailLocation])
    newVideo.gifLocation = newGifFullThumbnailLocation

    if request.form['videoTitle'] != "":
        newVideo.channelName = system.strip_html(request.form['videoTitle'])
    else:
        newVideo.channelName = currentTime

    newVideo.topic = topic

    newVideo.description = system.strip_html(request.form['videoDescription'])

    if os.path.isfile(videoPath):
        newVideo.pending = False
        db.session.add(newVideo)
        db.session.commit()

        if ChannelQuery.autoPublish is True:
            newVideo.published = True
        else:
            newVideo.published = False
        db.session.commit()

        if ChannelQuery.imageLocation is None:
            channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
        else:
            channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + ChannelQuery.imageLocation)
        system.newLog(4, "File Upload Successful - Username:" + current_user.username)

        if ChannelQuery.autoPublish is True:

            webhookFunc.runWebhook(ChannelQuery.id, 6, channelname=ChannelQuery.channelName,
                       channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(ChannelQuery.id)),
                       channeltopic=templateFilters.get_topicName(ChannelQuery.topic),
                       channelimage=channelImage, streamer=templateFilters.get_userName(ChannelQuery.owningUser),
                       channeldescription=str(ChannelQuery.description), videoname=newVideo.channelName,
                       videodate=newVideo.videoDate, videodescription=newVideo.description,
                       videotopic=templateFilters.get_topicName(newVideo.topic),
                       videourl=(sysSettings.siteProtocol + sysSettings.siteAddress + '/play/' + str(newVideo.id)),
                       videothumbnail=(sysSettings.siteProtocol + sysSettings.siteAddress + '/videos/' + newVideo.thumbnailLocation))

            subscriptionQuery = subscriptions.channelSubs.query.filter_by(channelID=ChannelQuery.id).all()
            for sub in subscriptionQuery:
                # Create Notification for Channel Subs
                newNotification = notifications.userNotification(templateFilters.get_userName(ChannelQuery.owningUser) + " has posted a new video to " + ChannelQuery.channelName + " titled " + newVideo.channelName, '/play/' + str(newVideo.id),
                                                                 "/images/" + ChannelQuery.owner.pictureLocation, sub.userID)
                db.session.add(newNotification)
            db.session.commit()

            try:
                subsFunc.processSubscriptions(ChannelQuery.id,
                                 sysSettings.siteName + " - " + ChannelQuery.channelName + " has posted a new video",
                                 "<html><body><img src='" + sysSettings.siteProtocol + sysSettings.siteAddress + sysSettings.systemLogo + "'><p>Channel " + ChannelQuery.channelName + " has posted a new video titled <u>" + newVideo.channelName +
                                 "</u> to the channel.</p><p>Click this link to watch<br><a href='" + sysSettings.siteProtocol + sysSettings.siteAddress + "/play/" + str(newVideo.id) + "'>" + newVideo.channelName + "</a></p>")
            except:
                system.newLog(0, "Subscriptions Failed due to possible misconfiguration")

    videoID = newVideo.id
    db.session.commit()
    db.session.close()
    flash("Video upload complete")
    return redirect(url_for('play.view_vid_page', videoID=videoID))