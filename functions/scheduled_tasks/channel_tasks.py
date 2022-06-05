from celery.canvas import subtask
from celery.result import AsyncResult

import datetime
import logging
from classes.shared import celery, db
from classes import Stream, Channel
from functions import xmpp, cachedDbCalls

log = logging.getLogger('app.functions.scheduler.channel_tasks')

def setup_channel_tasks(sender, **kwargs):
    sender.add_periodic_task(120, update_channel_counts.s(), name='Check Live Channel Counts')

@celery.task(bind=True)
def update_channel_counts(self):
    """
    Task to check live channels counts
    """
    streamQuery = Stream.Stream.query.filter_by(active=True).with_elements(Stream.Stream.id, Stream.Stream.linkedChannel).all()
    liveStreamCount = 0
    for stream in streamQuery:
        liveStreamCount = liveStreamCount + 1
        results = subtask('functions.scheduled_tasks.channel_tasks.update_channel_count', args=(stream.id, stream.linkedChannel)).apply_async()
    log.info("Scheduled Channel Update Performed on " + str(liveStreamCount) + " channels.")

@celery.task(bind=True)
def update_channel_count(self, streamId, channelId):
    channelQuery = cachedDbCalls.getChannel(channelId)
    if channelQuery is not None:
        count = xmpp.getChannelCounts(channelQuery.channelLoc)
        channelUpdate = Channel.Channel.query.filter_by(id=channelQuery.id).update(dict(currentViewers=count))
        streamUpdate = Stream.Stream.query.filter_by(id=streamId).update(dict(currentViewers=count))
        log.info("Update Channel/Stream Live Counts: " + str(channelQuery.channelLoc) + ":" + streamId + " to " + str(count))
