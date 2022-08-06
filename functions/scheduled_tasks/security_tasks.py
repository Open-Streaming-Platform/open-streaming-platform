from celery.canvas import subtask
from celery.result import AsyncResult

import datetime
import logging
from classes.shared import celery, db
from classes import Sec

from functions import securityFunc

log = logging.getLogger("app.functions.scheduler.security_tasks")


def setup_security_tasks(sender, **kwargs):
    sender.add_periodic_task(
        3600,
        check_flagged_for_delete_users.s(),
        name="Check and Delete Users Flagged for Deletion",
    )
    sender.add_periodic_task(
        3600,
        check_old_guests.s(),
        name="Check and Delete Stale Guest Users",
    )


@celery.task(bind=True)
def check_flagged_for_delete_users(self):
    """
    Task to Check Users Scheduled for Deletion and Initiate on time
    """
    results = Sec.UsersFlaggedForDeletion.query.filter(
        Sec.UsersFlaggedForDeletion.timestamp < datetime.datetime.now()
    ).all()
    for userFlag in results:
        deleteResult = securityFunc.delete_user(userFlag.userID)
        log.info(
            {
                "level": "info",
                "taskID": self.request.id.__str__(),
                "message": "Flagged User Deleted: "
                + str(userFlag.userID)
                + "/ "
                + str(userFlag.timestamp),
            }
        )
    db.session.commit()
    db.session.close()
    return True


@celery.task(bind=True)
def check_old_guests(self):
    """
    Task to check for Guest Entries in the DB and Delete those last active older than 3 months
    """
    guestDeleteCount = Sec.Guest.query.filter(
        Sec.Guest.last_active_at < datetime.datetime.now() - datetime.timedelta(days=90)
    ).count()
    results = Sec.Guest.query.filter(
        Sec.Guest.last_active_at < datetime.datetime.now() - datetime.timedelta(days=90)
    ).delete()
    db.session.commit()
    db.session.close()
    log.info(
        {
            "level": "info",
            "taskID": self.request.id.__str__(),
            "message": "Stale Guest Users Deleted: " + str(guestDeleteCount),
        }
    )
    return True
