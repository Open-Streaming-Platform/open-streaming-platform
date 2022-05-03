from celery.canvas import subtask
from celery.result import AsyncResult
import glob
import datetime
import logging
from classes.shared import celery, db
from classes import RecordedVideo, Channel, settings, subscriptions, notifications, Stream

from functions import videoFunc, cachedDbCalls, templateFilters, subsFunc, system
from functions.scheduled_tasks import message_tasks

log = logging.getLogger('app.functions.scheduler.video_tasks')

def setup_video_tasks(sender, **kwargs):
    sender.add_periodic_task(3600, check_video_thumbnails.s(), name='Check Video Thumbnails')
    sender.add_periodic_task(3600, check_video_retention.s(), name='Check Video Retention and Cleanup')
    sender.add_periodic_task(21600, check_video_published_exists.s(), name='Check Video Health')
    sender.add_periodic_task(3600, reprocess_stuck_videos.s(), name='Reprocess Stuck Videos')
    sender.add_periodic_task(3600, process_ingest_folder.s(), name="Process Folder Ingest")

@celery.task(bind=True)
def delete_video(self, videoID):
    """
    Task to delete a video
    """
    results = videoFunc.deleteVideo(videoID)
    log.info({"level": "info", "taskID": self.request.id.__str__(), "message": "Video Deleted: " + str(videoID)})
    return True

@celery.task(bind=True, time_limit=10800, soft_time_limit=7200)
def create_video_clip(self, videoID, clipStart, clipStop, clipName, clipDescription):
    """
    Task to create a video clip
    """
    results = videoFunc.createClip(videoID, clipStart, clipStop, clipName, clipDescription)
    log.info({"level": "info", "taskID": self.request.id.__str__(), "message": "Video Clip Created for: " + str(videoID)})
    return results[0]

@celery.task(bind=True)
def delete_video_clip(self, clipID):
    """
    Task to delete a video clip
    """
    results = videoFunc.deleteClip(clipID)
    log.info({"level": "info", "taskID": self.request.id.__str__(), "message": "Video Clip deleted: " + str(clipID)})
    return True

@celery.task(bind=True)
def update_video_thumbnail(self, videoID, timeStamp):
    """
    Task to update a video thumbnail
    """
    results = videoFunc.setVideoThumbnail(videoID, timeStamp)
    log.info({"level": "info", "taskID": self.request.id.__str__(), "message": "Updated Video Thumbnail - Updated: " + str(videoID)})
    return True

@celery.task(bind=True)
def check_video_thumbnails(self):
    """
    Validates that all Recorded Videos Contain Thumbnails
    """
    recordedVideoQuery = RecordedVideo.RecordedVideo.query.filter_by(pending=False, thumbnailLocation=None).with_entities(
        RecordedVideo.RecordedVideo.id).all()
    videosUpdated = []
    for video in recordedVideoQuery:
        results = videoFunc.setVideoThumbnail(video.id, 0)
        if results is True:
            videosUpdated.append(video.id)
    log.info({"level": "info", "taskID": self.request.id.__str__(), "message": "Validated Video Thumbnails - Updated: " + str(videosUpdated)})
    return True

@celery.task(bind=True)
def check_video_retention(self):
    """
    Checks if Server Retention or Channel Retention of Videos has been met and delete videos exceeding the lower of the two
    """
    currentTime = datetime.datetime.utcnow()
    sysSettings = settings.settings.query.first()
    videoCount = 0
    if sysSettings != None:
        channelQuery = Channel.Channel.query.all()
        for channel in channelQuery:
            if sysSettings.maxVideoRetention > 0 or channel.maxVideoRetention > 0:
                setRetentionArray = []
                if sysSettings.maxVideoRetention > 0:
                    setRetentionArray.append(sysSettings.maxVideoRetention)
                if channel.maxVideoRetention > 0:
                    setRetentionArray.append(channel.maxVideoRetention)
                setRetention = min(setRetentionArray)
                for video in channel.recordedVideo:
                    if currentTime - datetime.timedelta(days=setRetention) > video.videoDate:
                        results = subtask('functions.scheduled_tasks.video_tasks.delete_video', args=(video.id, )).apply_async()
                        videoCount = videoCount + 1
    log.info({"level": "info", "taskID": self.request.id.__str__(), "message": "Video Retention Check Performed.  Removed: " + str(videoCount)})
    return "Removed Videos " + str(videoCount)


@celery.task(bind=True)
def check_video_published_exists(self):
    """
    Checks the overall health of all videos by checking whether a video is published and the file exists
    """
    videoQuery = RecordedVideo.RecordedVideo.query.filter_by(published=True, pending=False).all()
    count = 0
    for video in videoQuery:
        videoResult = video.get_video_exists()
        if videoResult is False:
            vidId = video.id
            videoFunc.deleteVideo(video.id)
            log.info({"level": "warning", "taskID": self.request.id.__str__(),
                      "message": "Unhealthy Video Object Identified and Removed.  Removed: " + str(vidId)})
            count = count + 1
    return "Video Health Check Performed.  Removed " + str(count) + " video objects"

@celery.task(bind=True)
def reprocess_stuck_videos(self):
    """
    Reprocesses videos which are still pending=True, but stream has ended
    """
    count = 0
    videoQuery = RecordedVideo.RecordedVideo.query.filter_by(published=False, pending=True).all()
    for video in videoQuery:
        if video.videoLocation != '' and video.get_video_exists():
            streamQuery = Stream.Stream.query.filter_by(id=video.originalStreamID).first()
            if streamQuery is None:
                channelQuery = Channel.Channel.query.filter_by(id=video.channelID).first()
                results = subtask('functions.rtmpFunc.rtmp_rec_Complete_handler',
                                  args=(channelQuery.channelLoc, video.videoLocation), kwargs={'pendingVideoID': video.id}).apply_async()
                log.info({"level": "warning", "taskID": self.request.id.__str__(),
                          "message": "Reprocessing Stuck Video ID: " + video.id + ", Path: " + video.videoLocation})
                count = count + 1
    return "Performed Video Reprocessing.  Count: " + str(count)

@celery.task(bind=True)
def process_ingest_folder(self):
    channelFolders = glob.glob("/var/www/ingest/*/")
    videosProcessed = []
    channel = []
    for channelFolder in channelFolders:
        channelLoc = channelFolder.replace('/var/www/ingest/','')[:-1]
        channel.append(channelLoc)
        channelQuery = cachedDbCalls.getChannelByLoc(channelLoc)
        if channelQuery != None:
            pendingFiles = glob.glob("/var/www/ingest/" + channelLoc + "/*.mp4")
            for file in pendingFiles:
                videosProcessed.append(file)
                results = subtask('functions.video_tasks.process_video_upload',
                                  args=(file, '', channelQuery.topic, str(datetime.datetime.now()), '', channelQuery.id),
                                  kwargs=({'sourcePath': '/var/www/ingest/' + channelLoc})
                                  ).apply_async()
    return "Complete - " + str(videosProcessed)

@celery.task(bind=True)
def process_video_upload(self, videoFilename, thumbnailFilename, topic, videoTitle, videoDescription, channelId, sourcePath=None):
    """
    Processes Video Upload following user submittal
    """
    sysSettings = cachedDbCalls.getSystemSettings()

    #ChannelQuery = Channel.Channel.query.filter_by(id=channelId).first()
    ChannelQuery = cachedDbCalls.getChannel(channelId)
    if sourcePath != None:
        results = videoFunc.processVideoUpload(videoFilename, thumbnailFilename, topic, videoTitle, videoDescription, ChannelQuery, sourcePath=sourcePath)
    else:
        results = videoFunc.processVideoUpload(videoFilename, thumbnailFilename, topic, videoTitle, videoDescription, ChannelQuery)

    if results[0] == "Success":
        newVideo = results[1]
        if ChannelQuery.autoPublish is True:
            if ChannelQuery.imageLocation is None:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/static/img/video-placeholder.jpg")
            else:
                channelImage = (sysSettings.siteProtocol + sysSettings.siteAddress + "/images/" + ChannelQuery.imageLocation)
            subtaskResults = subtask('functions.scheduled_tasks.message_tasks.send_webhook', args=(ChannelQuery.id, 6),
                              kwargs={
                                  "channelurl": (sysSettings.siteProtocol + sysSettings.siteAddress + "/channel/" + str(ChannelQuery.id)),
                                  "channeltopic": templateFilters.get_topicName(ChannelQuery.topic),
                                  "channelimage": channelImage,
                                  "streamer": templateFilters.get_userName(ChannelQuery.owningUser),
                                  "channeldescription": str(ChannelQuery.description),
                                  "videoname": newVideo.channelName,
                                  "videodate": newVideo.videoDate,
                                  "videodescription": newVideo.description,
                                  "videotopic": templateFilters.get_topicName(newVideo.topic),
                                  "videourl": (sysSettings.siteProtocol + sysSettings.siteAddress + '/play/' + str(newVideo.id)),
                                  "videothumbnail": (sysSettings.siteProtocol + sysSettings.siteAddress + '/videos/' + newVideo.thumbnailLocation)
                              }
                              ).apply_async()

            subscriptionQuery = subscriptions.channelSubs.query.filter_by(channelID=ChannelQuery.id).all()
            for sub in subscriptionQuery:
                # Create Notification for Channel Subs
                newNotification = notifications.userNotification(
                    templateFilters.get_userName(ChannelQuery.owningUser) + " has posted a new video to "
                    + ChannelQuery.channelName + " titled " + newVideo.channelName, '/play/' + str(newVideo.id),
                    "/images/" + templateFilters.get_pictureLocation(ChannelQuery.owningUser), sub.userID)
                db.session.add(newNotification)
            db.session.commit()

            try:
                subsFunc.processSubscriptions(ChannelQuery.id,
                                              sysSettings.siteName + " - " + ChannelQuery.channelName + " has posted a new video",
                                              "<html><body><img src='" + sysSettings.siteProtocol + sysSettings.siteAddress + sysSettings.systemLogo + "'><p>Channel " + ChannelQuery.channelName + " has posted a new video titled <u>" + newVideo.channelName +
                                              "</u> to the channel.</p><p>Click this link to watch<br><a href='" + sysSettings.siteProtocol + sysSettings.siteAddress + "/play/" + str(
                                                  newVideo.id) + "'>" + newVideo.channelName + "</a></p>", "video")
            except:
                system.newLog(0, "Subscriptions Failed due to possible misconfiguration")
        return (results[0])
    else:
        return (results[0] + ":" + results[1])