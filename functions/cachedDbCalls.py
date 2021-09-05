from classes.shared import db

from classes import settings
from classes import Channel
from classes import RecordedVideo
from classes import Stream
from classes import subscriptions

from classes.shared import cache

@cache.memoize(timeout=50)
def getAllChannels():
    channelQuery = Channel.Channel.query.all()
    return channelQuery

