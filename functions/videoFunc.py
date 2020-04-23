import subprocess
import os
import shutil

from flask import current_app as app
from flask import flash
from flask_security import current_user

from classes.shared import db
from classes import Channel
from classes import RecordedVideo
from classes import upvotes
from classes import comments
from classes import views
from classes import settings

from functions import system
from functions import webhookFunc

# Checks Length of a Video at path and returns the length
def getVidLength(input_video):
    result = subprocess.check_output(['ffprobe', '-i', input_video, '-show_entries', 'format=duration', '-loglevel', '8', '-of', 'csv=%s' % ("p=0")])
    return float(result)

def deleteVideo(videoID):
    recordedVid = RecordedVideo.RecordedVideo.query.filter_by(id=videoID).first()

    if current_user.id == recordedVid.owningUser and recordedVid.videoLocation is not None:
        videos_root = app.config['WEB_ROOT'] + 'videos/'
        filePath = videos_root + recordedVid.videoLocation
        thumbnailPath = videos_root + recordedVid.videoLocation[:-4] + ".png"
        gifPath = videos_root + recordedVid.videoLocation[:-4] + ".gif"

        if filePath != videos_root:
            if os.path.exists(filePath) and (recordedVid.videoLocation is not None or recordedVid.videoLocation != ""):
                os.remove(filePath)
                if os.path.exists(thumbnailPath):
                    os.remove(thumbnailPath)
                if os.path.exists(gifPath):
                    os.remove(gifPath)

        # Delete Clips Attached to Video
        for clip in recordedVid.clips:
            thumbnailPath = videos_root + clip.thumbnailLocation

            if thumbnailPath != videos_root:
                if os.path.exists(thumbnailPath) and (
                        clip.thumbnailLocation is not None or clip.thumbnailLocation != ""):
                    os.remove(thumbnailPath)
            db.session.delete(clip)

        # Delete Upvotes Attached to Video
        upvoteQuery = upvotes.videoUpvotes.query.filter_by(videoID=recordedVid.id).all()

        for vote in upvoteQuery:
            db.session.delete(vote)

        # Delete Comments Attached to Video
        commentQuery = comments.videoComments.query.filter_by(videoID=recordedVid.id).all()

        for comment in commentQuery:
            db.session.delete(comment)

        # Delete Views Attached to Video
        viewQuery = views.views.query.filter_by(viewType=1, itemID=recordedVid.id).all()

        for view in viewQuery:
            db.session.delete(view)

        db.session.delete(recordedVid)

        db.session.commit()
        system.newLog(4, "Video Deleted - ID #" + str(videoID))
        return True
    return False

def changeVideoMetadata(videoID, newVideoName, newVideoTopic, description, allowComments):

    recordedVidQuery = RecordedVideo.RecordedVideo.query.filter_by(id=videoID, owningUser=current_user.id).first()
    sysSettings = settings.settings.query.first()

    if recordedVidQuery is not None:

        recordedVidQuery.channelName = strip_html(newVideoName)
        recordedVidQuery.topic = newVideoTopic
        recordedVidQuery.description = strip_html(description)
        recordedVidQuery.allowComments = allowComments

        if recordedVidQuery.channel.imageLocation is None:
            channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
        else:
            channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + recordedVidQuery.channel.imageLocation)

        webhookFunc.runWebhook(recordedVidQuery.channel.id, 9, channelname=recordedVidQuery.channel.channelName,
                   channelurl=(sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(recordedVidQuery.channel.id)),
                   channeltopic=get_topicName(recordedVidQuery.channel.topic),
                   channelimage=channelImage, streamer=get_userName(recordedVidQuery.channel.owningUser),
                   channeldescription=str(recordedVidQuery.channel.description), videoname=recordedVidQuery.channelName,
                   videodate=recordedVidQuery.videoDate, videodescription=recordedVidQuery.description,
                   videotopic=get_topicName(recordedVidQuery.topic),
                   videourl=(sysSettings.siteProtocol + sysSettings.siteAddress + '/videos/' + recordedVidQuery.videoLocation),
                   videothumbnail=(sysSettings.siteProtocol + sysSettings.siteAddress + '/videos/' + recordedVidQuery.thumbnailLocation))
        db.session.commit()
        system.newLog(4, "Video Metadata Changed - ID # " + str(recordedVidQuery.id))
        return True
    return False

def moveVideo(videoID, newChannel):

    recordedVidQuery = RecordedVideo.RecordedVideo.query.filter_by(id=int(videoID), owningUser=current_user.id).first()

    if recordedVidQuery is not None:
        newChannelQuery = Channel.Channel.query.filter_by(id=newChannel, owningUser=current_user.id).first()
        if newChannelQuery is not None:
            videos_root = app.config['WEB_ROOT'] + 'videos/'

            recordedVidQuery.channelID = newChannelQuery.id
            coreVideo = (recordedVidQuery.videoLocation.split("/")[1]).split("_", 1)[1]
            if not os.path.isdir(videos_root + newChannelQuery.channelLoc):
                try:
                    os.mkdir(videos_root + newChannelQuery.channelLoc)
                except OSError:
                    system.newLog(4, "Error Moving Video ID #" + str(recordedVidQuery.id) + "to Channel ID" + str(
                        newChannelQuery.id) + "/" + newChannelQuery.channelLoc)
                    flash("Error Moving Video - Unable to Create Directory", "error")
                    return False
            shutil.move(videos_root + recordedVidQuery.videoLocation,
                        videos_root + newChannelQuery.channelLoc + "/" + newChannelQuery.channelLoc + "_" + coreVideo)
            recordedVidQuery.videoLocation = newChannelQuery.channelLoc + "/" + newChannelQuery.channelLoc + "_" + coreVideo
            if (recordedVidQuery.thumbnailLocation is not None) and (
            os.path.exists(videos_root + recordedVidQuery.thumbnailLocation)):
                coreThumbnail = (recordedVidQuery.thumbnailLocation.split("/")[1]).split("_", 1)[1]
                coreThumbnailGif = (recordedVidQuery.gifLocation.split("/")[1]).split("_", 1)[1]
                shutil.move(videos_root + recordedVidQuery.thumbnailLocation,
                            videos_root + newChannelQuery.channelLoc + "/" + newChannelQuery.channelLoc + "_" + coreThumbnail)
                if (recordedVidQuery.gifLocation is not None) and (os.path.exists(videos_root + recordedVidQuery.gifLocation)):
                    shutil.move(videos_root + recordedVidQuery.gifLocation,
                                videos_root + newChannelQuery.channelLoc + "/" + newChannelQuery.channelLoc + "_" + coreThumbnailGif)
                recordedVidQuery.thumbnailLocation = newChannelQuery.channelLoc + "/" + newChannelQuery.channelLoc + "_" + coreThumbnail
                recordedVidQuery.gifLocation = newChannelQuery.channelLoc + "/" + newChannelQuery.channelLoc + "_" + coreThumbnailGif
            for clip in recordedVidQuery.clips:
                coreThumbnail = (clip.thumbnailLocation.split("/")[2])
                if not os.path.isdir(videos_root + newChannelQuery.channelLoc + '/clips'):
                    try:
                        os.mkdir(videos_root + newChannelQuery.channelLoc + '/clips')
                    except OSError:
                        system.newLog(4, "Error Moving Video ID #" + str(recordedVidQuery.id) + "to Channel ID" + str(
                            newChannelQuery.id) + "/" + newChannelQuery.channelLoc)
                        flash("Error Moving Video - Unable to Create Clips Directory", "error")
                        return False
                newClipLocation = videos_root + newChannelQuery.channelLoc + "/clips/" + coreThumbnail
                shutil.move(videos_root + clip.thumbnailLocation, newClipLocation)
                clip.thumbnailLocation = newChannelQuery.channelLoc + "/clips/" + coreThumbnail

            db.session.commit()
            system.newLog(4, "Video ID #" + str(recordedVidQuery.id) + "Moved to Channel ID" + str(
                newChannelQuery.id) + "/" + newChannelQuery.channelLoc)
            return True
    return False