from celery.canvas import subtask
from celery.result import AsyncResult

import datetime
import logging
from classes.shared import celery
from classes import RecordedVideo, Channel, settings

from functions import videoFunc

log = logging.getLogger('app.functions.scheduler.video_tasks')

def setup_video_tasks(sender, **kwargs):
    sender.add_periodic_task(3600, check_video_thumbnails.s(), name='Check Video Thumbnails')
    sender.add_periodic_task(3600, check_video_retention.s(), name='Check Video Retention and Cleanup')

@celery.task(bind=True)
def delete_video(self, videoID):
    """
    Task to delete a video
    """
    results = videoFunc.deleteVideo(videoID)
    log.info({"level": "info", "taskID": self.request.id.__str__(), "message": "Video Deleted: " + str(videoID)})
    return True

@celery.task(bind=True)
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
