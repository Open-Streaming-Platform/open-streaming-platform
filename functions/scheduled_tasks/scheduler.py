import logging
from celery.decorators import periodic_task
from celery.schedules import crontab
from classes.shared import celery

from functions.scheduled_tasks import video_tasks

from datetime import timedelta

log = logging.getLogger('app.functions.scheduler')

@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls test('hello') every 10 seconds.
    video_tasks.setup_video_tasks(sender, **kwargs)



