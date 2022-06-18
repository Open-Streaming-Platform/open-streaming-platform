import logging

from classes.shared import db
from functions import notifications

log = logging.getLogger('app.functions.celery')

def on_failure(self, exc, task_id, args, kwargs, einfo):
    # exc (Exception) - The exception raised by the task.
    # args (Tuple) - Original arguments for the task that failed.
    # kwargs (Dict) - Original keyword arguments for the task that failed.

    db.session.rollback()

    errorMsg = "A Background Task has failed: " + str(task_id) + ", Error: " + str(exc), ", args: " + str(args) + ", kwargs: " + str(kwargs)
    notifications.sendAdminNotification(errorMsg, "/settings/admin", "/static/img/logo.png")
    log.error(errorMsg)