import subprocess
import os
import shutil
import logging
import datetime
import pathlib
import uuid
from typing import Union

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


def getVidLength(input_video: str) -> float:
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


def deleteVideo(videoID: int) -> bool:
    recordedVid = RecordedVideo.RecordedVideo.query.filter_by(id=videoID).with_entities(RecordedVideo.RecordedVideo.id, RecordedVideo.RecordedVideo.videoLocation, RecordedVideo.RecordedVideo.channelID).first()

    if recordedVid.videoLocation is not None:
        videos_root = globalvars.videoRoot + "videos/"
        filePath = videos_root + recordedVid.videoLocation
        thumbnailPath = videos_root + recordedVid.videoLocation[:-4] + ".png"
        gifPath = videos_root + recordedVid.videoLocation[:-4] + ".gif"

        videoTags = RecordedVideo.video_tags.query.filter_by(
            videoID=recordedVid.id
        ).delete()

        # Delete Upvotes Attached to Video
        upvoteQuery = upvotes.videoUpvotes.query.filter_by(videoID=recordedVid.id).delete()

        # Delete Comments Attached to Video
        commentQuery = comments.videoComments.query.filter_by(
            videoID=recordedVid.id
        ).delete()

        # Delete Views Attached to Video
        viewQuery = views.views.query.filter_by(viewType=1, itemID=recordedVid.id).delete()

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

        recordedVid = RecordedVideo.RecordedVideo.query.filter_by(id=videoID).delete()

        db.session.commit()
        system.newLog(4, "Video Deleted - ID #" + str(videoID))
        return True
    return False


def changeVideoMetadata(
    videoID: int, newVideoName: str, newVideoTopic: int, description: str, allowComments: bool
) -> bool:

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


def moveVideo(videoID: int, newChannel: int):

    recordedVidQuery = RecordedVideo.RecordedVideo.query.filter_by(
        id=int(videoID), owningUser=current_user.id
    ).with_entities(RecordedVideo.RecordedVideo.id, RecordedVideo.RecordedVideo.videoLocation, RecordedVideo.RecordedVideo.thumbnailLocation, RecordedVideo.RecordedVideo.gifLocation).first()

    if recordedVidQuery is not None:
        newChannelQuery = Channel.Channel.query.filter_by(
            id=newChannel, owningUser=current_user.id
        ).with_entities(Channel.Channel.id, Channel.Channel.channelLoc).first()
        if newChannelQuery is not None:
            videos_root = globalvars.videoRoot + "videos/"

            coreVideo = (recordedVidQuery.videoLocation.split("/")[1]).split("_", 1)[1]
            if not os.path.isdir(videos_root + newChannelQuery.channelLoc):
                try:
                    os.mkdir(videos_root + newChannelQuery.channelLoc)
                except OSError:
                    system.newLog(4,f"Error Moving Video ID # {str(recordedVidQuery.id)} to Channel ID {str(newChannelQuery.id)}/{newChannelQuery.channelLoc}",)
                    flash("Error Moving Video - Unable to Create Directory", "error")
                    return False
            shutil.move(f"{videos_root}{recordedVidQuery.videoLocation}", f"{videos_root}{newChannelQuery.channelLoc}/{newChannelQuery.channelLoc}_{coreVideo}")

            updatedVideoLocation = f"{newChannelQuery.channelLoc}/{newChannelQuery.channelLoc}_{coreVideo}"

            recordedVid = RecordedVideo.RecordedVideo.query.filter_by(id=recordedVidQuery.id).update(dict(videoLocation=updatedVideoLocation, channelID=newChannelQuery.id))

            if (recordedVidQuery.thumbnailLocation is not None) and (
                os.path.exists(videos_root + recordedVidQuery.thumbnailLocation)
            ):
                coreThumbnail = (
                    recordedVidQuery.thumbnailLocation.split("/")[1]
                ).split("_", 1)[1]
                coreThumbnailGif = (recordedVidQuery.gifLocation.split("/")[1]).split(
                    "_", 1
                )[1]
                shutil.move(f"{videos_root}{recordedVidQuery.thumbnailLocation}", f"{videos_root}{newChannelQuery.channelLoc}/{newChannelQuery.channelLoc}_{coreThumbnail}",)
                if (recordedVidQuery.gifLocation is not None) and (
                    os.path.exists(videos_root + recordedVidQuery.gifLocation)
                ):
                    shutil.move(f"{videos_root}{recordedVidQuery.gifLocation}", f"{videos_root}{newChannelQuery.channelLoc}/{newChannelQuery.channelLoc}_{coreThumbnailGif}",)
                
                newThumbnailLocation = f"{newChannelQuery.channelLoc}/{newChannelQuery.channelLoc}_{coreThumbnail}"
                newGifLocation = f"{newChannelQuery.channelLoc}/{newChannelQuery.channelLoc}_{coreThumbnailGif}"

                recordedVid = RecordedVideo.RecordedVideo.query.filter_by(id=recordedVidQuery.id).update(dict(thumbnailLocation=newThumbnailLocation, gifLocation=newGifLocation))
            for clip in RecordedVideo.Clips.query.filter_by(parentVideo=recordedVidQuery.id).with_entities(RecordedVideo.Clips.id).all():
                destClipFolderAbsPath = os.path.join(videos_root, newChannelQuery.channelLoc, "clips")
                if not os.path.isdir(destClipFolderAbsPath):
                    try:
                        os.mkdir(destClipFolderAbsPath)
                    except OSError:
                        system.newLog(4,f"Error Moving Video ID #{str(recordedVidQuery.id)} to Channel ID {str(newChannelQuery.id)}/{newChannelQuery.channelLoc}",)
                        flash("Error Moving Video - Unable to Create Clips Directory","error",)
                        return False
                clipQuery = RecordedVideo.Clips.query.filter_by(id=clip.id).update(channelID=newChannelQuery.id)
                moveClips(clip.id, videos_root, newChannelQuery.channelLoc)

            db.session.commit()
            system.newLog(4,f"Video ID #{str(recordedVidQuery.id)} Moved to Channel ID {str(newChannelQuery.id)}/{newChannelQuery.channelLoc}",)
            return True
    return False


def createClip(videoID: int, clipStart: float, clipStop: float, clipName: int, clipDescription: str) -> tuple[bool, int | None]:
    settingsQuery = cachedDbCalls.getSystemSettings()

    # TODO Add Webhook for Clip Creation
    recordedVidQuery = cachedDbCalls.getVideo(videoID)

    if recordedVidQuery is not None:

        clipLocationName = str(uuid.uuid4())

        clipLength = clipStop - clipStart
        if settingsQuery.maxClipLength < 301:
            if clipLength > settingsQuery.maxClipLength:
                return False, None

        if clipStop > clipStart:
            videos_root = os.path.join(globalvars.videoRoot, "videos")

            # Generate Clip Object
            newClip = RecordedVideo.Clips(
                datetime.datetime.now(datetime.timezone.utc),
                recordedVidQuery,
                None,
                clipStart,
                clipStop,
                clipName,
                clipDescription,
            )
            clipFilesName = f"clip-{newClip.id}"
            newClip.published = False

            channelLocation = str(cachedDbCalls.getChannelLocationFromID(recordedVidQuery.channelID))
            
            # Establish Locations for Clips and Thumbnails
            clipFilesPath = os.path.join(channelLocation, "clips", clipFilesName)

            # Set Clip Object Values for Locations
            newClip.videoLocation = f"{clipFilesPath}.mp4"
            newClip.thumbnailLocation = f"{clipFilesPath}.png"
            newClip.gifLocation = f"{clipFilesPath}.gif"
            db.session.add(newClip)
            db.session.commit()

            newClipQuery = RecordedVideo.Clips.query.filter_by(id=newClip.id).with_entities(
                RecordedVideo.Clips.id,
                RecordedVideo.Clips.videoLocation,
                RecordedVideo.Clips.thumbnailLocation,
                RecordedVideo.Clips.gifLocation,
                RecordedVideo.Clips.startTime,
                RecordedVideo.Clips.length).first()

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

            updateClipQuery = RecordedVideo.Clips.query.filter_by(id=newClipQuery.id).update(dict(published=True))

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
                newNotification = notifications.userNotification(f"{templateFilters.get_userName(recordedVidQuery.owningUser)} has posted a new clip to {recordedVidQuery.channel.channelName} titled {clipName}",
                    f"/clip/{str(newClipQuery.id)}",
                    f"/images/{str(recordedVidQuery.channel.owner.pictureLocation)}",
                    sub.userID,
                )
                db.session.add(newNotification)

            db.session.commit()
            db.session.close()
            return True, redirectID
    return False, None


def generateClipFiles(clip, videosRoot: str, sourceVideoLocation: str) -> None:
    # Set Full Path for Locations to be handled by FFMPEG
    fullvideoLocation = os.path.join(videosRoot, clip.videoLocation)
    fullthumbnailLocation = os.path.join(videosRoot, clip.thumbnailLocation)
    fullgifLocation = os.path.join(videosRoot, clip.gifLocation)

    # FFMPEG Subprocess to generate clip's files - video, thumbnail, and gif.
    clipVideo = subprocess.call(['/usr/bin/ffmpeg', '-hwaccel', 'auto', '-ss', str(clip.startTime), '-t', str(clip.length), '-i', sourceVideoLocation, fullvideoLocation])
    processResult = subprocess.call(['/usr/bin/ffmpeg', '-hwaccel', 'auto', '-ss', str(clip.startTime), '-i', sourceVideoLocation, '-s', '384x216', '-vframes', '1', fullthumbnailLocation])
    gifprocessResult = subprocess.call(
        [
            "/usr/bin/ffmpeg",
            '-hwaccel', 
            'auto',
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

def moveClips(clipId: int, videosRoot: str, destChannelLoc: str) -> bool:

    clipQuery = RecordedVideo.Clips.query.filter_by(id=clipId).with_entities(RecordedVideo.Clips.id, RecordedVideo.Clips.videoLocation, RecordedVideo.Clips.thumbnailLocation, RecordedVideo.Clips.gifLocation).all()
    clipFilesNewPath = os.path.join(
        destChannelLoc, "clips", os.path.basename(clipQuery.videoLocation).replace(".mp4", "")
    )

    newMp4LocationValue = f"{clipFilesNewPath}.mp4"
    newPngLocationValue = f"{clipFilesNewPath}.png"
    newGifLocationValue = f"{clipFilesNewPath}.gif"

    shutil.move(
        os.path.join(videosRoot, clipQuery.videoLocation), os.path.join(videosRoot, newMp4LocationValue), 
    )
    shutil.move(
        os.path.join(videosRoot, clipQuery.thumbnailLocation), os.path.join(videosRoot, newPngLocationValue), 
    )
    shutil.move(
        os.path.join(videosRoot, clipQuery.gifLocation), os.path.join(videosRoot, newGifLocationValue), 
    )

    clipUpdate = RecordedVideo.Clips.query.filter_by(id=clipQuery.id).update(dict(videoLocation=newMp4LocationValue, thumbnailLocation=newPngLocationValue, gifLocation=newGifLocationValue))
    db.session.commit()

    return True

def getClipCreationTimeFromFiles(clip: RecordedVideo.Clips) -> None:
    mp4AbsPath = os.path.join(globalvars.videoRoot, "videos", clip.videoLocation)
    if not os.path.exists(mp4AbsPath):
        raise Exception(f"could not find .mp4 file for clip #{clip.id}")
    
    earliestDatetime = None
    statResults = os.stat(mp4AbsPath)
    try:
        earliestDatetime = datetime.datetime.fromtimestamp(statResults.st_birthtime, datetime.timezone.utc)
    except AttributeError as e:
        currentDatetime = None
        earliestDatetime = datetime.datetime.fromtimestamp(statResults.st_ctime, datetime.timezone.utc)

        currentDatetime = datetime.datetime.fromtimestamp(statResults.st_mtime, datetime.timezone.utc)
        if currentDatetime < earliestDatetime:
            earliestDatetime = currentDatetime

        currentDatetime = datetime.datetime.fromtimestamp(statResults.st_atime, datetime.timezone.utc)
        if currentDatetime < earliestDatetime:
            earliestDatetime = currentDatetime
    clipUpdate = RecordedVideo.Clips.query.filter_by(id=clip.id).update(dict(clipDate=earliestDatetime))

    db.session.commit()


def changeClipMetadata(clipID: int, name: str, topicID: int, description: str, clipTags: list) -> bool:
    # TODO Add Webhook for Clip Metadata Change

    clipQuery = RecordedVideo.Clips.query.filter_by(id=int(clipID)).with_entities(RecordedVideo.Clips.id, RecordedVideo.Clips.owningUser).first()

    if clipQuery is not None:
        if (
            clipQuery.owningUser == current_user.id
            or current_user.has_role("Admin")
        ):

            clipUpdate = RecordedVideo.Clips.query.filter_by(id=clipQuery.id).update(dict(clipName=system.strip_html(name), description=system.strip_html(description), topic=topicID))

            if clipTags != None:
                tagArray = system.parseTags(clipTags)
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
            system.newLog(6, f"Clip Metadata Changed - ID #{str(clipID)}")
            return True
    return False


def deleteClip(clipID: int) -> bool:
    clipQuery = RecordedVideo.Clips.query.filter_by(id=int(clipID)).with_entities(RecordedVideo.Clips.id, RecordedVideo.Clips.videoLocation, RecordedVideo.Clips.thumbnailLocation, RecordedVideo.Clips.gifLocation).first()
    videos_root = globalvars.videoRoot + "videos/"

    if clipQuery is not None:

        clipTagsDelete = RecordedVideo.clip_tags.query.filter_by(clipID=clipQuery.id).delete()

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

        upvoteQueryDelete = upvotes.clipUpvotes.query.filter_by(clipID=clipQuery.id).delete()

        owningChannelQuery = cachedDbCalls.getClipChannelID(clipQuery.id)
        if owningChannelQuery is not None:
            channelQuery = cachedDbCalls.getChannel(owningChannelQuery)
            if channelQuery is not None:
                cache.delete_memoized(cachedDbCalls.getAllClipsForChannel_View, channelQuery.id)
                cache.delete_memoized(cachedDbCalls.getAllClipsForUser, channelQuery.owningUser)

        deleteClipQuery = RecordedVideo.Clips.query.filter_by(id=clipQuery.id).delete()

        db.session.commit()
        system.newLog(6, f"Clip Deleted - ID #{str(clipID)}")
        log.info(f"Clip Deleted - ID: {str(clipID)}")
        return True
    else:
        log.warning(f"Attempted to Delete Non-Existing Clip - ID: {str(clipID)}")
        return False


def setVideoThumbnail(videoID: int, timeStamp: datetime.datetime) -> bool:
    videos_root = globalvars.videoRoot + "videos/"

    videoQuery = cachedDbCalls.getVideo(videoID)
    if videoQuery is not None:
        videoLocation = videos_root + videoQuery.videoLocation
        newThumbnailLocation = videoQuery.videoLocation[:-3] + "png"
        newGifThumbnailLocation = videoQuery.videoLocation[:-3] + "gif"

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
                '-hwaccel', 
                'auto',
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
                '-hwaccel',
                'auto',
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
    videoFilename: str,
    thumbnailFilename: str,
    topic: int,
    videoTitle: str,
    videoDescription: str,
    ChannelQuery,
    sourcePath: Union[str, None] = None,
) -> tuple:
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
    videoLoc = f"{ChannelQuery.channelLoc}/{newFileNameGUID}_{datetime.datetime.strftime(currentTime, '%Y%m%d_%H%M%S')}.mp4"
    videos_root = current_app.config["WEB_ROOT"] + "videos/"
    videoPath = videos_root + videoLoc

    if videoFilename != "":
        if not os.path.isdir(videos_root + ChannelQuery.channelLoc):
            try:
                os.mkdir(videos_root + ChannelQuery.channelLoc)
            except OSError:
                system.newLog(4,f"File Upload Failed - OSError - Unable to Create Directory - Channel:{ChannelQuery.channelLoc}",)
                db.session.close()
                return ("Error", "Error uploading video - Unable to create directory")
        if sourcePath is None:
            sourcePath = current_app.config["VIDEO_UPLOAD_TEMPFOLDER"]
        shutil.move(f"{sourcePath}/{videoFilename}", videoPath)
    else:
        db.session.close()
        return ("Error", "Error uploading video - Couldn't move video file")

    newVideo.videoLocation = videoLoc

    if thumbnailFilename != "":
        thumbnailLoc = f"{ChannelQuery.channelLoc}/{newFileNameGUID}_{datetime.datetime.strftime(currentTime, '%Y%m%d_%H%M%S')}{videoFilename.rsplit('.', 1)[-1]}"

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
        thumbnailLoc = f"{ChannelQuery.channelLoc}/{newFileNameGUID}_{datetime.datetime.strftime(currentTime, '%Y%m%d_%H%M%S')}.png"

        subprocess.call(
            [
                "/usr/bin/ffmpeg",
                '-hwaccel',
                'auto',
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

    newGifFullThumbnailLocation = f"{ChannelQuery.channelLoc}/{newFileNameGUID}_{datetime.datetime.strftime(currentTime, '%Y%m%d_%H%M%S')}.gif"
    gifresult = subprocess.call(
        [
            "/usr/bin/ffmpeg",
            '-hwaccel',
            'auto',
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
        system.newLog(4, f"File Upload Successful - Channel: {ChannelQuery.channelLoc}")

        return ("Success", newVideo)
    else:
        return ("Failure", "Video File Missing")


def processFLVUpload(path: str) -> bool:
    destinationPath = path.replace("flv", "mp4")

    processedStreamVideo = subprocess.call(
        [
            "/usr/bin/ffmpeg",
            '-hwaccel',
            'auto',
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


def processStreamVideo(path: str, channelLoc: str) -> bool:

    inputPath = globalvars.videoRoot + "pending/" + path
    destinationPath = f"{globalvars.videoRoot}videos/{channelLoc}/{path.replace('flv', 'mp4')}"

    processedStreamVideo = subprocess.call(
        [
            "/usr/bin/ffmpeg",
            '-hwaccel',
            'auto',
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
