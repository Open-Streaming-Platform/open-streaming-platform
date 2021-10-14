import logging
from classes.shared import celery
from classes import RecordedVideo

from functions import videoFunc

log = logging.getLogger('app.functions.scheduler.video_tasks')

def setup_video_tasks(sender, **kwargs):
    sender.add_periodic_task(3600, check_video_thumbnails.s(), name='Check Video Thumbnails')

@celery.task()
def update_video_thumbnail(videoID, timeStamp):
    """
    Task to update a video thumbnail
    """
    results = videoFunc.setVideoThumbnail(videoID, timeStamp)
    #log.info({"level": "info", "taskID": "self.request.id", "message": "Updated Video Thumbnail - Updated: " + str(videoID)})
    return True

@celery.task(bind=True)
def check_video_thumbnails():
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
    log.info({"level": "info", "taskID": "self.request.id", "message": "Validated Video Thumbnails - Updated: " + str(videosUpdated)})
    return True


