from celery.canvas import subtask
from celery.result import AsyncResult

import logging
from classes.shared import celery, db
from classes import notifications, Sec

from functions import notifications

log = logging.getLogger('app.functions.scheduler.message_tasks')

def setup_message_tasks(sender, **kwargs):
    pass

@celery.task(bind=True)
def send_message(self, subject, message, fromUser, toUser):
    result = notifications.sendMessage(subject, message, fromUser, toUser)
    log.info({"level": "info", "taskID": self.request.id.__str__(), "message": "Message Sent", "subject": subject, "from": fromUser, "to": toUser})
    return True

@celery.task(bind=True)
def send_mass_message(self, subject, message, fromUser):
    for user in Sec.User.query.all():
        results = subtask('functions.scheduled_tasks.message_tasks.send_message', args=(subject, message, fromUser, user.id )).apply_async()
    log.info({"level": "info", "taskID": self.request.id.__str__(), "message": "Mass Message Sent", "subject": subject, "from": fromUser})
    return True