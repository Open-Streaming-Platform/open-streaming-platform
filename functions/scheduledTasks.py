import logging
from celery.decorators import periodic_task
from celery.schedules import crontab
from classes.shared import celery

from datetime import timedelta

log = logging.getLogger('app.functions.securityFunctions')

@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls test('hello') every 10 seconds.
    sender.add_periodic_task(10.0, test.s('hello'), name='add every 10')

@celery.task
def test(arg):
    print(arg)

