from classes import Channel
from classes.shared import celery

@celery.task
def pullChannelsTest():
    channelQuery = Channel.Channel.query.all()
    channelQuery2 = Channel.Channel.query.all()
    return channelQuery