import subprocess
import os
import shutil
import logging
import datetime
import pathlib
import uuid

from flask import flash, current_app
from flask_security import current_user

from globals import globalvars

from classes.shared import db, cache
from classes import Channel
from classes import RecordedVideo
from classes import upvotes
from classes import comments
from classes import views
from classes import settings
from classes import subscriptions
from classes import notifications

from functions import system
from functions import templateFilters
from functions import cachedDbCalls

log = logging.getLogger("app.functions.database")

# Checks Length of a Video at path and returns the length


def getVidLength(input_video):
    result = subprocess.check_output(
        [
            "/usr/bin/ffprobe",
            "-i",
            input_video,
            "-show_entries",
            "format=duration",
            "-loglevel",
            "8",
            "-of",
            "csv=%s" % ("p=0"),
        ]
    )
    return float(result)


def deleteVideo(videoID):
    recordedVid = RecordedVideo.RecordedVideo.query.filter_by(id=videoID).first()

    if recordedVid.videoLocation is not None:
        videos_root = globalvars.videoRoot + "videos/"
        filePath = videos_root + recordedVid.videoLocation
        thumbnailPath = videos_root + recordedVid.videoLocation[:-4] + ".png"
        gifPath = videos_root + recordedVid.videoLocation[:-4] + ".gif"

        videoTags = RecordedVideo.video_tags.query.filter_by(
            videoID=recordedVid.id
        ).all()
        for tag in videoTags:
            db.session.delete(tag)

        # Delete Clips Attached to Video
        for clip in recordedVid.clips:
            deleteClip(clip.id)

        # Delete Upvotes Attached to Video
        upvoteQuery = upvotes.videoUpvotes.query.filter_by(videoID=recordedVid.id).all()

        for vote in upvoteQuery:
            db.session.delete(vote)

        # Delete Comments Attached to Video
        commentQuery = comments.videoComments.query.filter_by(
            videoID=recordedVid.id
        ).all()

        for comment in commentQuery:
            db.session.delete(comment)

        # Delete Views Attached to Video
        viewQuery = views.views.query.filter_by(viewType=1, itemID=recordedVid.id).all()

        for view in viewQuery:
            db.session.delete(view)

        # Delete Video and Thumbnails
        if filePath != videos_root:
            if os.path.exists(filePath) and (
                recordedVid.videoLocation is not None or recordedVid.videoLocation != ""
            ):
                os.remove(filePath)
                if os.path.exists(thumbnailPath):
                    os.remove(thumbnailPath)
                if os.path.exists(gifPath):
                    os.remove(gifPath)

        cache.delete_memoized(cachedDbCalls.getChannelVideos, recordedVid.channelID)
        cache.delete_memoized(cachedDbCalls.getAllVideo_View, recordedVid.channelID)
        cache.delete_memoized(cachedDbCalls.getVideo, recordedVid.id)

        db.session.delete(recordedVid)

        db.session.commit()
        system.newLog(4, "Video Deleted - ID #" + str(videoID))
        return True
    return False


def changeVideoMetadata(
    videoID, newVideoName, newVideoTopic, description, allowComments
):

    recordedVidQuery = cachedDbCalls.getVideo(videoID)
    sysSettings = cachedDbCalls.getSystemSettings()

    if recordedVidQuery is not None:
        updateVideo = RecordedVideo.RecordedVideo.query.filter_by(
            id=recordedVidQuery.id
        ).update(
            dict(
                channelName=system.strip_html(newVideoName),
                topic=newVideoTopic,
                description=system.strip_html(description),
                allowComments=allowComments,
            )
        )
        # recordedVidQuery.channelName = system.strip_html(newVideoName)
        # recordedVidQuery.topic = newVideoTopic
        # recordedVidQuery.description = system.strip_html(description)
        # recordedVidQuery.allowComments = allowComments
        cachedDbCalls.invalidateVideoCache(recordedVidQuery.id)

        recordedVidQuery = cachedDbCalls.getVideo(videoID)
        channelQuery = cachedDbCalls.getChannel(recordedVidQuery.channelID)

        if channelQuery.imageLocation is None:
            channelImage = (
                sysSettings.siteProtocol
                + sysSettings.siteAddress
                + "/static/img/video-placeholder.jpg"
            )
        else:
            channelImage = (
                sysSettings.siteProtocol
                + sysSettings.siteAddress
                + "/images/"
                + channelQuery.imageLocation
            )

        from functions.scheduled_tasks import message_tasks
        message_tasks.send_webhook.delay(
            channelQuery.id,
            9,
            channelname=channelQuery.channelName,
            channelurl=(
                sysSettings.siteProtocol
                + sysSettings.siteAddress
                + "/channel/"
                + str(channelQuery.id)
            ),
            channeltopic=templateFilters.get_topicName(channelQuery.topic),
            channelimage=channelImage,
            streamer=templateFilters.get_userName(recordedVidQuery.owningUser),
            channeldescription=str(channelQuery.description),
            videoname=recordedVidQuery.channelName,
            videodate=recordedVidQuery.videoDate,
            videodescription=recordedVidQuery.description,
            videotopic=templateFilters.get_topicName(recordedVidQuery.topic),
            videourl=(
                sysSettings.siteProtocol
                + sysSettings.siteAddress
                + "/videos/"
                + recordedVidQuery.videoLocation
            ),
            videothumbnail=(
                sysSettings.siteProtocol
                + sysSettings.siteAddress
                + "/videos/"
                + recordedVidQuery.thumbnailLocation
            ),
        )
        db.session.commit()
        system.newLog(4, "Video Metadata Changed - ID # " + str(recordedVidQuery.id))
        return True
    return False


def moveVideo(videoID, newChannel):

    recordedVidQuery = RecordedVideo.RecordedVideo.query.filter_by(
        id=int(videoID), owningUser=current_user.id
    ).first()

    if recordedVidQuery is not None:
        newChannelQuery = Channel.Channel.query.filter_by(
            id=newChannel, owningUser=current_user.id
        ).first()
        if newChannelQuery is not None:
            videos_root = globalvars.videoRoot + "videos/"

            recordedVidQuery.channelID = newChannelQuery.id
            coreVideo = (recordedVidQuery.videoLocation.split("/")[1]).split("_", 1)[1]
            if not os.path.isdir(videos_root + newChannelQuery.channelLoc):
                try:
                    os.mkdir(videos_root + newChannelQuery.channelLoc)
                except OSError:
                    system.newLog(
                        4,
                        "Error Moving Video ID #"
                        + str(recordedVidQuery.id)
                        + "to Channel ID"
                        + str(newChannelQuery.id)
                        + "/"
                        + newChannelQuery.channelLoc,
                    )
                    flash("Error Moving Video - Unable to Create Directory", "error")
                    return False
            shutil.move(
                videos_root + recordedVidQuery.videoLocation,
                videos_root
                + newChannelQuery.channelLoc
                + "/"
                + newChannelQuery.channelLoc
                + "_"
                + coreVideo,
            )
            recordedVidQuery.videoLocation = (
                newChannelQuery.channelLoc
                + "/"
                + newChannelQuery.channelLoc
                + "_"
                + coreVideo
            )
            if (recordedVidQuery.thumbnailLocation is not None) and (
                os.path.exists(videos_root + recordedVidQuery.thumbnailLocation)
            ):
                coreThumbnail = (
                    recordedVidQuery.thumbnailLocation.split("/")[1]
                ).split("_", 1)[1]
                coreThumbnailGif = (recordedVidQuery.gifLocation.split("/")[1]).split(
                    "_", 1
                )[1]
                shutil.move(
                    videos_root + recordedVidQuery.thumbnailLocation,
                    videos_root
                    + newChannelQuery.channelLoc
                    + "/"
                    + newChannelQuery.channelLoc
                    + "_"
                    + coreThumbnail,
                )
                if (recordedVidQuery.gifLocation is not None) and (
                    os.path.exists(videos_root + recordedVidQuery.gifLocation)
                ):
                    shutil.move(
                        videos_root + recordedVidQuery.gifLocation,
                        videos_root
                        + newChannelQuery.channelLoc
                        + "/"
                        + newChannelQuery.channelLoc
                        + "_"
                        + coreThumbnailGif,
                    )
                recordedVidQuery.thumbnailLocation = (
                    newChannelQuery.channelLoc
                    + "/"
                    + newChannelQuery.channelLoc
                    + "_"
                    + coreThumbnail
                )
                recordedVidQuery.gifLocation = (
                    newChannelQuery.channelLoc
                    + "/"
                    + newChannelQuery.channelLoc
                    + "_"
                    + coreThumbnailGif
                )
            for clip in recordedVidQuery.clips:
                coreThumbnail = clip.thumbnailLocation.split("/")[2]
                if not os.path.isdir(
                    videos_root + newChannelQuery.channelLoc + "/clips"
                ):
                    try:
                        os.mkdir(videos_root + newChannelQuery.channelLoc + "/clips")
                    except OSError:
                        system.newLog(
                            4,
                            "Error Moving Video ID #"
                            + str(recordedVidQuery.id)
                            + "to Channel ID"
                            + str(newChannelQuery.id)
                            + "/"
                            + newChannelQuery.channelLoc,
                        )
                        flash(
                            "Error Moving Video - Unable to Create Clips Directory",
                            "error",
                        )
                        return False
                newClipLocation = (
                    videos_root + newChannelQuery.channelLoc + "/clips/" + coreThumbnail
                )
                shutil.move(videos_root + clip.thumbnailLocation, newClipLocation)
                clip.thumbnailLocation = (
                    newChannelQuery.channelLoc + "/clips/" + coreThumbnail
                )

            db.session.commit()
            system.newLog(
                4,
                "Video ID #"
                + str(recordedVidQuery.id)
                + "Moved to Channel ID"
                + str(newChannelQuery.id)
                + "/"
                + newChannelQuery.channelLoc,
            )
            return True
    return False


def createClip(videoID, clipStart, clipStop, clipName, clipDescription):
    settingsQuery = cachedDbCalls.getSystemSettings()

    # TODO Add Webhook for Clip Creation
    recordedVidQuery = RecordedVideo.RecordedVideo.query.filter_by(
        id=int(videoID)
    ).first()

    if recordedVidQuery is not None:

        clipLength = clipStop - clipStart
        if settingsQuery.maxClipLength < 301:
            if clipLength > settingsQuery.maxClipLength:
                return False, None

        if clipStop > clipStart:
            videos_root = os.path.join(globalvars.videoRoot, "videos")

            # Generate Clip Object
            newClip = RecordedVideo.Clips(
                recordedVidQuery.id,
                None,
                clipStart,
                clipStop,
                clipName,
                clipDescription,
            )
            newClip.published = False
            db.session.add(newClip)
            db.session.commit()

            newClipQuery = RecordedVideo.Clips.query.filter_by(id=newClip.id).first()
            channelLocation = recordedVidQuery.channel.channelLoc
            
            # Establish Locations for Clips and Thumbnails
            clipFilesPath = os.path.join(channelLocation, "clips", f"clip-{newClipQuery.id}")

            # Set Clip Object Values for Locations
            newClipQuery.videoLocation = f"{clipFilesPath}.mp4"
            newClipQuery.thumbnailLocation = f"{clipFilesPath}.png"
            newClipQuery.gifLocation = f"{clipFilesPath}.gif"

            clipFolderAbsPath = os.path.join(videos_root, channelLocation, "clips")
            # Create Clip Directory if doesn't exist
            if not os.path.isdir(clipFolderAbsPath):
                os.mkdir(clipFolderAbsPath)

            generateClipFiles(
                newClipQuery,
                videos_root,
                os.path.join(videos_root, recordedVidQuery.videoLocation)
            )

            redirectID = newClipQuery.id
            newClipQuery.published = True
            system.newLog(6, "New Clip Created - ID #" + str(redirectID))

            cache.delete_memoized(
                cachedDbCalls.getAllClipsForChannel_View, recordedVidQuery.channelID
            )
            cache.delete_memoized(
                cachedDbCalls.getAllClipsForUser, recordedVidQuery.owningUser
            )

            subscriptionQuery = subscriptions.channelSubs.query.filter_by(
                channelID=recordedVidQuery.channel.id
            ).all()
            for sub in subscriptionQuery:
                # Create Notification for Channel Subs
                newNotification = notifications.userNotification(
                    templateFilters.get_userName(recordedVidQuery.owningUser)
                    + " has posted a new clip to "
                    + recordedVidQuery.channel.channelName
                    + " titled "
                    + clipName,
                    "/clip/" + str(newClipQuery.id),
                    "/images/" + str(recordedVidQuery.channel.owner.pictureLocation),
                    sub.userID,
                )
                db.session.add(newNotification)

            db.session.commit()
            db.session.close()
            return True, redirectID
    return False, None


def generateClipFiles(clip, videosRoot, sourceVideoLocation):
    # Set Full Path for Locations to be handled by FFMPEG
    fullvideoLocation = os.path.join(videosRoot, clip.videoLocation)
    fullthumbnailLocation = os.path.join(videosRoot, clip.thumbnailLocation)
    fullgifLocation = os.path.join(videosRoot, clip.gifLocation)

    # FFMPEG Subprocess to generate clip's files - video, thumbnail, and gif.
    clipVideo = subprocess.call(['/usr/bin/ffmpeg', '-ss', str(clip.startTime), '-t', str(clip.length), '-i', sourceVideoLocation, fullvideoLocation])
    processResult = subprocess.call(['/usr/bin/ffmpeg', '-ss', str(clip.startTime), '-i', sourceVideoLocation, '-s', '384x216', '-vframes', '1', fullthumbnailLocation])
    gifprocessResult = subprocess.call(
        [
            "/usr/bin/ffmpeg",
            '-ss',
            str(clip.startTime),
            "-t",
            str(3),
            "-i",
            sourceVideoLocation,
            "-filter_complex",
            "[0:v] fps=30,scale=w=384:h=-1,split [a][b];[a] palettegen=stats_mode=single [p];[b][p] paletteuse=new=1",
            "-y",
            fullgifLocation,
        ]
    )


def changeClipMetadata(clipID, name, description, clipTags):
    # TODO Add Webhook for Clip Metadata Change

    clipQuery = RecordedVideo.Clips.query.filter_by(id=int(clipID)).first()

    if clipQuery is not None:
        if (
            clipQuery.recordedVideo.owningUser == current_user.id
            or current_user.has_role("Admin")
        ):

            clipQuery.clipName = system.strip_html(name)
            clipQuery.description = system.strip_html(description)

            if clipTags != None:
                videoTagString = clipTags
                tagArray = system.parseTags(videoTagString)
                existingTagArray = RecordedVideo.clip_tags.query.filter_by(
                    clipID=clipID
                ).all()

                for currentTag in existingTagArray:
                    if currentTag.name not in tagArray:
                        db.session.delete(currentTag)
                    else:
                        tagArray.remove(currentTag.name)
                db.session.commit()
                for currentTag in tagArray:
                    newTag = RecordedVideo.clip_tags(
                        currentTag, clipID, current_user.id
                    )
                    db.session.add(newTag)
                    db.session.commit()

            db.session.commit()
            system.newLog(6, "Clip Metadata Changed - ID #" + str(clipID))
            return True
    return False


def deleteClip(clipID):
    clipQuery = RecordedVideo.Clips.query.filter_by(id=int(clipID)).first()
    videos_root = globalvars.videoRoot + "videos/"

    if clipQuery is not None:

        clipTags = RecordedVideo.clip_tags.query.filter_by(clipID=clipQuery.id).all()
        for tag in clipTags:
            db.session.delete(tag)

        videoPath = None
        if clipQuery.videoLocation is not None:
            videoPath = videos_root + clipQuery.videoLocation
        if clipQuery.thumbnailLocation is not None:
            thumbnailPath = videos_root + clipQuery.thumbnailLocation
        else:
            thumbnailPath = None
        if clipQuery.gifLocation is not None:
            gifPath = videos_root + clipQuery.gifLocation
        else:
            gifPath = None

        if thumbnailPath != videos_root and thumbnailPath is not None:
            if os.path.exists(thumbnailPath) and (
                thumbnailPath is not None or thumbnailPath != ""
            ):
                os.remove(thumbnailPath)
        if gifPath != videos_root and gifPath is not None:
            if os.path.exists(gifPath) and (
                clipQuery.gifLocation is not None or gifPath != ""
            ):
                os.remove(gifPath)
        if videoPath != videos_root and videoPath is not None:
            if os.path.exists(videoPath) and (
                clipQuery.videoLocation is not None or videoPath != ""
            ):
                os.remove(videoPath)

        upvoteQuery = upvotes.clipUpvotes.query.filter_by(clipID=clipQuery.id).all()
        for vote in upvoteQuery:
            db.session.delete(vote)
        owningChannelQuery = cachedDbCalls.getClipChannelID(clipQuery.id)
        channelQuery = cachedDbCalls.getChannel(owningChannelQuery)
        cache.delete_memoized(cachedDbCalls.getAllClipsForChannel_View, channelQuery.id)
        cache.delete_memoized(cachedDbCalls.getAllClipsForUser, channelQuery.owningUser)

        db.session.delete(clipQuery)

        db.session.commit()
        system.newLog(6, "Clip Deleted - ID #" + str(clipID))
        log.info("Clip Deleted - ID: " + str(clipID))
        return True
    else:
        log.warning("Attempted to Delete Non-Existing Clip - ID: " + str(clipID))
        return False


def setVideoThumbnail(videoID, timeStamp):
    videos_root = globalvars.videoRoot + "videos/"

    videoQuery = cachedDbCalls.getVideo(videoID)
    if videoQuery is not None:
        videoLocation = videos_root + videoQuery.videoLocation
        newThumbnailLocation = videoQuery.videoLocation[:-3] + "png"
        newGifThumbnailLocation = videoQuery.videoLocation[:-3] + "gif"
        # videoQuery.thumbnailLocation = newThumbnailLocation
        fullthumbnailLocation = videos_root + newThumbnailLocation
        newGifFullThumbnailLocation = videos_root + newGifThumbnailLocation

        updateVideoQuery = RecordedVideo.RecordedVideo.query.filter_by(
            id=videoID
        ).update(
            dict(
                thumbnailLocation=newThumbnailLocation,
                gifLocation=newGifThumbnailLocation,
            )
        )
        # videoQuery.thumbnailLocation = newThumbnailLocation
        # videoQuery.gifLocation = newGifThumbnailLocation

        db.session.commit()
        db.session.close()
        try:
            os.remove(fullthumbnailLocation)
        except OSError:
            pass
        try:
            os.remove(newGifFullThumbnailLocation)
        except OSError:
            pass
        result = subprocess.call(
            [
                "/usr/bin/ffmpeg",
                "-ss",
                str(timeStamp),
                "-i",
                videoLocation,
                "-s",
                "384x216",
                "-vframes",
                "1",
                fullthumbnailLocation,
            ]
        )
        gifresult = subprocess.call(
            [
                "/usr/bin/ffmpeg",
                "-ss",
                str(timeStamp),
                "-t",
                "3",
                "-i",
                videoLocation,
                "-filter_complex",
                "[0:v] fps=30,scale=w=384:h=-1,split [a][b];[a] palettegen=stats_mode=single [p];[b][p] paletteuse=new=1",
                "-y",
                newGifFullThumbnailLocation,
            ]
        )
        return True
    else:
        return False


def processVideoUpload(
    videoFilename,
    thumbnailFilename,
    topic,
    videoTitle,
    videoDescription,
    ChannelQuery,
    sourcePath=None,
):
    currentTime = datetime.datetime.utcnow()

    videoPublishState = ChannelQuery.autoPublish

    newVideo = RecordedVideo.RecordedVideo(
        ChannelQuery.owningUser,
        ChannelQuery.id,
        ChannelQuery.channelName,
        ChannelQuery.topic,
        0,
        "",
        currentTime,
        ChannelQuery.allowComments,
        videoPublishState,
    )

    newFileNameGUID = str(uuid.uuid4())
    videoLoc = (
        ChannelQuery.channelLoc
        + "/"
        + newFileNameGUID
        + "_"
        + datetime.datetime.strftime(currentTime, "%Y%m%d_%H%M%S")
        + ".mp4"
    )
    videos_root = current_app.config["WEB_ROOT"] + "videos/"
    videoPath = videos_root + videoLoc

    if videoFilename != "":
        if not os.path.isdir(videos_root + ChannelQuery.channelLoc):
            try:
                os.mkdir(videos_root + ChannelQuery.channelLoc)
            except OSError:
                system.newLog(
                    4,
                    "File Upload Failed - OSError - Unable to Create Directory - Channel:"
                    + ChannelQuery.channelLoc,
                )
                db.session.close()
                return ("Error", "Error uploading video - Unable to create directory")
        if sourcePath is None:
            sourcePath = current_app.config["VIDEO_UPLOAD_TEMPFOLDER"]
        shutil.move(sourcePath + "/" + videoFilename, videoPath)
    else:
        db.session.close()
        return ("Error", "Error uploading video - Couldn't move video file")

    newVideo.videoLocation = videoLoc

    if thumbnailFilename != "":
        thumbnailLoc = (
            ChannelQuery.channelLoc
            + "/"
            + newFileNameGUID
            + "_"
            + datetime.datetime.strftime(currentTime, "%Y%m%d_%H%M%S")
            + videoFilename.rsplit(".", 1)[-1]
        )

        thumbnailPath = videos_root + thumbnailLoc
        try:
            shutil.move(
                current_app.config["VIDEO_UPLOAD_TEMPFOLDER"] + "/" + thumbnailFilename,
                thumbnailPath,
            )
        except:
            pass
        newVideo.thumbnailLocation = thumbnailLoc
    else:
        thumbnailLoc = (
            ChannelQuery.channelLoc
            + "/"
            + newFileNameGUID
            + "_"
            + datetime.datetime.strftime(currentTime, "%Y%m%d_%H%M%S")
            + ".png"
        )

        subprocess.call(
            [
                "/usr/bin/ffmpeg",
                "-ss",
                "00:00:01",
                "-i",
                videos_root + videoLoc,
                "-s",
                "384x216",
                "-vframes",
                "1",
                videos_root + thumbnailLoc,
            ]
        )
        newVideo.thumbnailLocation = thumbnailLoc

    newGifFullThumbnailLocation = (
        ChannelQuery.channelLoc
        + "/"
        + newFileNameGUID
        + "_"
        + datetime.datetime.strftime(currentTime, "%Y%m%d_%H%M%S")
        + ".gif"
    )
    gifresult = subprocess.call(
        [
            "/usr/bin/ffmpeg",
            "-ss",
            "00:00:01",
            "-t",
            "3",
            "-i",
            videos_root + videoLoc,
            "-filter_complex",
            "[0:v] fps=30,scale=w=384:h=-1,split [a][b];[a] palettegen=stats_mode=single [p];[b][p] paletteuse=new=1",
            "-y",
            videos_root + newGifFullThumbnailLocation,
        ]
    )
    newVideo.gifLocation = newGifFullThumbnailLocation

    if videoTitle != "":
        newVideo.channelName = system.strip_html(videoTitle)
    else:
        newVideo.channelName = currentTime

    newVideo.topic = topic

    newVideo.description = system.strip_html(videoDescription)

    if os.path.isfile(videoPath):
        newVideo.pending = False
        duration = None
        try:
            duration = getVidLength(videoPath)
        except:
            pass
        if duration is not None:
            newVideo.length = duration
        db.session.add(newVideo)
        db.session.commit()

        if ChannelQuery.autoPublish is True:
            newVideo.published = True
        else:
            newVideo.published = False
        db.session.commit()
        system.newLog(4, "File Upload Successful - Channel:" + ChannelQuery.channelLoc)

        return ("Success", newVideo)
    else:
        return ("Failure", "Video File Missing")


def processFLVUpload(path):
    destinationPath = path.replace("flv", "mp4")

    processedStreamVideo = subprocess.call(
        [
            "/usr/bin/ffmpeg",
            "-y",
            "-i",
            path,
            "-codec",
            "copy",
            "-movflags",
            "+faststart",
            destinationPath,
        ]
    )

    destinationFilePath = pathlib.Path(destinationPath)
    if destinationFilePath.is_file() == False:
        return False

    oldFilePath = pathlib.Path(path)
    oldFilePath.unlink()

    return True


def processStreamVideo(path, channelLoc):

    inputPath = globalvars.videoRoot + "pending/" + path
    destinationPath = (
        globalvars.videoRoot + "videos/" + channelLoc + "/" + path.replace("flv", "mp4")
    )

    processedStreamVideo = subprocess.call(
        [
            "/usr/bin/ffmpeg",
            "-y",
            "-i",
            inputPath,
            "-codec",
            "copy",
            "-movflags",
            "+faststart",
            destinationPath,
        ]
    )

    destinationFilePath = pathlib.Path(destinationPath)
    if destinationFilePath.is_file() == False:
        return False

    oldFilePath = pathlib.Path(inputPath)
    oldFilePath.unlink()

    return True
