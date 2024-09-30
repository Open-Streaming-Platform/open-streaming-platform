from celery.canvas import subtask
from celery.result import AsyncResult
import glob
import datetime
import logging
import os
from flask import current_app

from classes.shared import celery, db
from classes import (
    RecordedVideo,
    Channel,
    settings,
    subscriptions,
    notifications,
    Stream,
)

from functions import videoFunc, cachedDbCalls, templateFilters, subsFunc, system
from functions.scheduled_tasks import message_tasks

log = logging.getLogger("app.functions.scheduler.video_tasks")


def setup_video_tasks(sender, **kwargs):
    sender.add_periodic_task(
        3600, check_video_thumbnails.s(), name="Check Video Thumbnails"
    )
    sender.add_periodic_task(
        3600, check_video_retention.s(checkVideos=True, checkClips=True), name="Check Video + Clip Retention and Cleanup"
    )
    sender.add_periodic_task(
        21600, check_video_published_exists.s(), name="Check Video Health"
    )
    sender.add_periodic_task(
        3600, reprocess_stuck_videos.s(), name="Reprocess Stuck Videos"
    )
    sender.add_periodic_task(
        3600, process_ingest_folder.s(), name="Process Folder Ingest"
    )


@celery.task(bind=True)
def delete_video(self, videoID):
    """
    Task to delete a video
    """
    results = videoFunc.deleteVideo(videoID)
    log.info(
        {
            "level": "info",
            "taskID": self.request.id.__str__(),
            "message": "Video Deleted: " + str(videoID),
        }
    )
    return True


@celery.task(bind=True)
def delete_clip(self, clipID):
    """
    Task to delete a video
    """
    results = videoFunc.deleteClip(clipID)
    log.info(
        {
            "level": "info",
            "taskID": self.request.id.__str__(),
            "message": "Clip Deleted: " + str(clipID),
        }
    )
    return True


@celery.task(bind=True, time_limit=10800, soft_time_limit=7200)
def create_video_clip(self, videoID, clipStart, clipStop, clipName, clipDescription):
    """
    Task to create a video clip
    """
    results = videoFunc.createClip(
        videoID, clipStart, clipStop, clipName, clipDescription
    )
    log.info(
        {
            "level": "info",
            "taskID": self.request.id.__str__(),
            "message": "Video Clip Created for: " + str(videoID),
        }
    )
    return results[0]


@celery.task(bind=True)
def delete_video_clip(self, clipID):
    """
    Task to delete a video clip
    """
    results = videoFunc.deleteClip(clipID)
    log.info(
        {
            "level": "info",
            "taskID": self.request.id.__str__(),
            "message": "Video Clip deleted: " + str(clipID),
        }
    )
    return True


@celery.task(bind=True)
def update_video_thumbnail(self, videoID, timeStamp):
    """
    Task to update a video thumbnail
    """
    results = videoFunc.setVideoThumbnail(videoID, timeStamp)
    log.info(
        {
            "level": "info",
            "taskID": self.request.id.__str__(),
            "message": "Updated Video Thumbnail - Updated: " + str(videoID),
        }
    )
    return True


@celery.task(bind=True)
def check_video_thumbnails(self):
    """
    Validates that all Recorded Videos Contain Thumbnails
    """
    recordedVideoQuery = (
        RecordedVideo.RecordedVideo.query.filter_by(
            pending=False, thumbnailLocation=None
        )
        .with_entities(RecordedVideo.RecordedVideo.id)
        .all()
    )
    videosUpdated = []
    for video in recordedVideoQuery:
        results = videoFunc.setVideoThumbnail(video.id, 0)
        if results is True:
            videosUpdated.append(video.id)
    log.info(
        {
            "level": "info",
            "taskID": self.request.id.__str__(),
            "message": "Validated Video Thumbnails - Updated: " + str(videosUpdated),
        }
    )
    return True


@celery.task(bind=True)
def check_video_retention(self, checkVideos=True, checkClips=False):
    """
    Checks if Server Retention or Channel Retention of Videos/Clips has been met and delete videos/clips exceeding the lower of the two
    """
    if not (checkVideos or checkClips):
        return "Invalid check_video_retention call. Must check videos or clips, or both."

    currentTime = datetime.datetime.utcnow()
    sysSettings = cachedDbCalls.getSystemSettings()
    videoCount = 0
    clipCount = 0

    if sysSettings == None:
        return "Could not get system settings"

    globalMVR = sysSettings.maxVideoRetention
    globalMCR = sysSettings.maxClipRetention

    channelQuery = Channel.Channel.query.with_entities(
        Channel.Channel.id, Channel.Channel.maxVideoRetention, Channel.Channel.maxClipRetention
    ).all()
    for channel in channelQuery:
        if checkClips and (globalMCR > 0 or channel.maxClipRetention > 0):
            finalClipRetention = globalMCR
            if globalMCR > 0 and channel.maxClipRetention > 0:
                finalClipRetention = min(globalMCR, channel.maxClipRetention)
            elif channel.maxClipRetention > 0:
                finalClipRetention = channel.maxClipRetention

            if finalClipRetention > 0:
                clipQuery = (
                    RecordedVideo.Clips.query.filter(
                        RecordedVideo.Clips.channelID == channel.id,
                        RecordedVideo.Clips.clipDate < currentTime - datetime.timedelta(days=finalClipRetention)
                    )
                    .with_entities(
                        RecordedVideo.Clips.id
                    )
                    .all()
                )
                for clip in clipQuery:
                    results = subtask(
                        "functions.scheduled_tasks.video_tasks.delete_clip",
                        args=(clip.id,)
                    ).apply_async()
                    clipCount = clipCount + 1
        if checkVideos and (globalMVR > 0 or channel.maxVideoRetention > 0):
            finalVideoRetention = globalMVR
            if globalMVR > 0 and channel.maxVideoRetention > 0:
                finalVideoRetention = min(globalMVR, channel.maxVideoRetention)
            elif channel.maxVideoRetention > 0:
                finalVideoRetention = channel.maxVideoRetention

            if finalVideoRetention > 0:
                VideoQuery = (
                    RecordedVideo.RecordedVideo.query.filter(
                        RecordedVideo.RecordedVideo.channelID == channel.id,
                        RecordedVideo.RecordedVideo.videoDate < currentTime - datetime.timedelta(days=finalVideoRetention)
                    )
                    .with_entities(
                        RecordedVideo.RecordedVideo.id
                    )
                    .all()
                )
                for video in VideoQuery:
                    results = subtask(
                        "functions.scheduled_tasks.video_tasks.delete_video",
                        args=(video.id,)
                    ).apply_async()
                    videoCount = videoCount + 1

    if checkVideos:
        log.info(
            {
                "level": "info",
                "taskID": self.request.id.__str__(),
                "message": "Video Retention Check Performed.  Removed: " + str(videoCount),
            }
        )
    if checkClips:
        log.info(
            {
                "level": "info",
                "taskID": self.request.id.__str__(),
                "message": "Clip Retention Check Performed.  Removed: " + str(clipCount),
            }
        )

    if checkVideos and checkClips:
        return f"Removed {str(videoCount)} Videos and {str(clipCount)} Clips"
    if checkClips:
        return f"Removed {str(clipCount)} Clips"
    return f"Removed {str(videoCount)} Videos"


@celery.task(bind=True)
def check_video_published_exists(self):
    """
    Checks the overall health of all videos by checking whether a video is published and the file exists
    """
    videoQuery = RecordedVideo.RecordedVideo.query.filter_by(
        published=True, pending=False
    ).all()
    count = 0
    for video in videoQuery:
        videoResult = video.get_video_exists()
        if videoResult is False:
            vidId = video.id
            videoFunc.deleteVideo(video.id)
            log.info(
                {
                    "level": "warning",
                    "taskID": self.request.id.__str__(),
                    "message": "Unhealthy Video Object Identified and Removed.  Removed: "
                    + str(vidId),
                }
            )
            count = count + 1
    return "Video Health Check Performed.  Removed " + str(count) + " video objects"


@celery.task(bind=True)
def reprocess_stuck_videos(self):
    """
    Reprocesses videos which are still pending=True, but stream has ended
    """
    count = 0
    videoQuery = RecordedVideo.RecordedVideo.query.filter_by(
        published=False, pending=True
    ).all()
    for video in videoQuery:
        if video.videoLocation != "" and video.get_video_exists():
            streamQuery = Stream.Stream.query.filter_by(
                id=video.originalStreamID, active=False, complete=True, pending=False
            ).first()
            if streamQuery is not None:
                channelQuery = cachedDbCalls.getChannel(video.channelID)
                results = subtask(
                    "functions.scheduled_tasks.rtmpFunc.rtmp_rec_Complete_handler",
                    args=(channelQuery.channelLoc, video.videoLocation),
                    kwargs={"pendingVideoID": video.id},
                ).apply_async()
                log.info(
                    {
                        "level": "warning",
                        "taskID": self.request.id.__str__(),
                        "message": "Reprocessing Stuck Video ID: "
                        + video.id
                        + ", Path: "
                        + video.videoLocation,
                    }
                )
                count = count + 1
    return "Performed Video Reprocessing.  Count: " + str(count)


@celery.task(bind=True)
def process_ingest_folder(self):
    vidRoot = current_app.config["WEB_ROOT"]
    if vidRoot["-1"] == '/':
        vidRoot = vidRoot[:-1]
    if not os.path.isdir(vidRoot + "ingest"):
        try:
            os.mkdir(vidRoot + "ingest")
        except:
            return "Fail: Ingest Folder Does Not Exist and Can Not Create"
    channelFolders = glob.glob(vidRoot + "ingest/*/")
    videosProcessed = []
    for channelFolder in channelFolders:
        channelLoc = channelFolder.replace(vidRoot + "ingest/", "")[:-1]
        channelQuery = cachedDbCalls.getChannelByLoc(channelLoc)
        if channelQuery != None:
            # Process MP4 Files
            pendingFiles = glob.glob(vidRoot + "ingest/" + channelLoc + "/*.mp4")
            for file in pendingFiles:
                filename = file.replace(vidRoot + "ingest/" + channelLoc + "/", "")

                videosProcessed.append(file)
                results = subtask(
                    "functions.scheduled_tasks.video_tasks.process_video_upload",
                    args=(
                        filename,
                        "",
                        channelQuery.topic,
                        filename,
                        f"{ filename } Imported at { str(datetime.datetime.now()) }",
                        channelQuery.id,
                    ),
                    kwargs=({"sourcePath": vidRoot + "ingest/" + channelLoc}),
                ).apply_async()

            # Process FLV Files
            pendingFiles = glob.glob(vidRoot + "ingest/" + channelLoc + "/*.flv")
            for file in pendingFiles:
                videoFunc.processFLVUpload(file)

                filename = file.replace(
                    vidRoot + "ingest/" + channelLoc + "/", ""
                ).replace(".flv", ".mp4")

                videosProcessed.append(file)
                results = subtask(
                    "functions.scheduled_tasks.video_tasks.process_video_upload",
                    args=(
                        filename,
                        "",
                        channelQuery.topic,
                        filename,
                        f"{ filename } Imported at { str(datetime.datetime.now()) }",
                        channelQuery.id,
                    ),
                    kwargs=({"sourcePath": vidRoot + "ingest/" + channelLoc}),
                ).apply_async()

    log.info(
        {
            "level": "info",
            "taskID": self.request.id.__str__(),
            "message": "Processed Video Uploads - Path: " + str(videosProcessed),
        }
    )
    return "Complete - " + str(videosProcessed)


@celery.task(bind=True)
def process_video_upload(
    self,
    videoFilename,
    thumbnailFilename,
    topic,
    videoTitle,
    videoDescription,
    channelId,
    sourcePath=None,
):
    """
    Processes Video Upload following user submittal
    """
    sysSettings = cachedDbCalls.getSystemSettings()

    # ChannelQuery = Channel.Channel.query.filter_by(id=channelId).first()
    ChannelQuery = cachedDbCalls.getChannel(channelId)
    if sourcePath != None:
        results = videoFunc.processVideoUpload(
            videoFilename,
            thumbnailFilename,
            topic,
            videoTitle,
            videoDescription,
            ChannelQuery,
            sourcePath=sourcePath,
        )
    else:
        results = videoFunc.processVideoUpload(
            videoFilename,
            thumbnailFilename,
            topic,
            videoTitle,
            videoDescription,
            ChannelQuery,
        )

    if results[0] == "Success":
        newVideo = results[1]
        if ChannelQuery.autoPublish is True:
            if ChannelQuery.imageLocation is None:
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
                    + ChannelQuery.imageLocation
                )
            subtaskResults = subtask(
                "functions.scheduled_tasks.message_tasks.send_webhook",
                args=(ChannelQuery.id, 6),
                kwargs={
                    "channelurl": (
                        sysSettings.siteProtocol
                        + sysSettings.siteAddress
                        + "/channel/"
                        + str(ChannelQuery.id)
                    ),
                    "channeltopic": templateFilters.get_topicName(ChannelQuery.topic),
                    "channelimage": channelImage,
                    "streamer": templateFilters.get_userName(ChannelQuery.owningUser),
                    "channeldescription": str(ChannelQuery.description),
                    "videoname": newVideo.channelName,
                    "videodate": newVideo.videoDate,
                    "videodescription": newVideo.description,
                    "videotopic": templateFilters.get_topicName(newVideo.topic),
                    "videourl": (
                        sysSettings.siteProtocol
                        + sysSettings.siteAddress
                        + "/play/"
                        + str(newVideo.id)
                    ),
                    "videothumbnail": (
                        sysSettings.siteProtocol
                        + sysSettings.siteAddress
                        + "/videos/"
                        + newVideo.thumbnailLocation
                    ),
                },
            ).apply_async()

            subscriptionQuery = subscriptions.channelSubs.query.filter_by(
                channelID=ChannelQuery.id
            ).all()
            for sub in subscriptionQuery:
                # Create Notification for Channel Subs
                newNotification = notifications.userNotification(
                    templateFilters.get_userName(ChannelQuery.owningUser)
                    + " has posted a new video to "
                    + ChannelQuery.channelName
                    + " titled "
                    + newVideo.channelName,
                    "/play/" + str(newVideo.id),
                    "/images/"
                    + templateFilters.get_pictureLocation(ChannelQuery.owningUser),
                    sub.userID,
                )
                db.session.add(newNotification)
            db.session.commit()

            try:
                subsFunc.processSubscriptions(
                    ChannelQuery.id,
                    sysSettings.siteName
                    + " - "
                    + ChannelQuery.channelName
                    + " has posted a new video",
                    "<html><body><img src='"
                    + sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + sysSettings.systemLogo
                    + "'><p>Channel "
                    + ChannelQuery.channelName
                    + " has posted a new video titled <u>"
                    + newVideo.channelName
                    + "</u> to the channel.</p><p>Click this link to watch<br><a href='"
                    + sysSettings.siteProtocol
                    + sysSettings.siteAddress
                    + "/play/"
                    + str(newVideo.id)
                    + "'>"
                    + newVideo.channelName
                    + "</a></p>",
                    "video",
                )
            except:
                system.newLog(
                    0, "Subscriptions Failed due to possible misconfiguration"
                )
        return results[0]
    else:
        return results[0] + ":" + results[1]
