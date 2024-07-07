from celery.canvas import subtask
from celery.result import AsyncResult

import datetime
import logging
from classes.shared import celery, db
from classes import Stream, Channel
from functions import xmpp, cachedDbCalls

log = logging.getLogger("app.functions.scheduler.channel_tasks")


def setup_channel_tasks(sender, **kwargs):
    #sender.add_periodic_task(120, update_channel_counts.s(), name='Check Live Channel Counts')
    pass


@celery.task(bind=True)
def update_channel_counts(self):
    """
    Task to check live channels counts
    """
    streamQuery = (
        Stream.Stream.query.filter_by(active=True)
        .with_entities(Stream.Stream.id, Stream.Stream.linkedChannel)
        .all()
    )
    liveStreamCount = 0
    for stream in streamQuery:
        liveStreamCount = liveStreamCount + 1
        results = subtask(
            "functions.scheduled_tasks.channel_tasks.update_channel_count",
            args=(stream.id, stream.linkedChannel),
        ).apply_async()
    log.info(
        "Scheduled Channel Update Performed on " + str(liveStreamCount) + " channels."
    )


@celery.task(bind=True)
def update_channel_count(self, streamId, channelId):
    channelQuery = cachedDbCalls.getChannel(channelId)
    if channelQuery is not None:
        count = xmpp.getChannelCounts(channelQuery.channelLoc)
        channelUpdate = Channel.Channel.query.filter_by(id=channelQuery.id).update(
            dict(currentViewers=count)
        )
        streamUpdate = Stream.Stream.query.filter_by(id=streamId).update(
            dict(currentViewers=count)
        )
        log.info(
            "Update Channel/Stream Live Counts: "
            + str(channelQuery.channelLoc)
            + ":"
            + str(streamId)
            + " to "
            + str(count)
        )

@celery.task(bind=True)
def check_channel_stream_time(self, streamId):
    activeStreamQuery = Stream.Stream.query.filer_by(id=streamId, active=True).with_entities(Stream.Stream.id, Stream.Stream.linkedChannel, Stream.Stream.startTimestamp).first()
    if activeStreamQuery is not None:
        channelId = activeStreamQuery.linkedChannel
        channelQuery = cachedDbCalls.getChannel(channelId)
        if channelQuery != None:
            streamTime = (datetime.datetime.utcnow() - activeStreamQuery.startTimeStamp)
            streamTimeMins = streamTime.total_seconds() / 60.0

@celery.task(bind=True)
def add_new_global_chat_mod_to_channels(self, user_id, user_uuid):
    for channel in Channel.Channel.query.with_entities(
        Channel.Channel.owningUser, Channel.Channel.channelLoc,
    ).all():
        new_affiliation = "admin"
        if channel.owningUser == user_id:
            new_affiliation = "owner"

        xmpp.set_user_affiliation(user_uuid, channel.channelLoc, new_affiliation)

@celery.task(bind=True)
def remove_global_chat_mod_from_channels(self, user_id, user_uuid):
    for channel in Channel.Channel.query.with_entities(
        Channel.Channel.owningUser, Channel.Channel.channelLoc,
    ).all():
        new_affiliation = "member"
        if channel.owningUser == user_id:
            new_affiliation = "owner"

        xmpp.set_user_affiliation(user_uuid, channel.channelLoc, new_affiliation)