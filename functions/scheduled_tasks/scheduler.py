import logging
from celery.schedules import crontab
from classes.shared import celery

from functions.scheduled_tasks import video_tasks, message_tasks, security_tasks

from datetime import timedelta

log = logging.getLogger('app.functions.scheduler')

@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Sets up Scheduled Tasks to be handled by Celery Beat
    """
    video_tasks.setup_video_tasks(sender, **kwargs)
    message_tasks.setup_message_tasks(sender, **kwargs)
    security_tasks.setup_security_tasks(sender, **kwargs)




