from flask_security import current_user

from classes.shared import db
from classes.shared import cache

from classes import topics, Channel, RecordedVideo

from functions import cachedDbCalls, system

from globals import globalvars


def deleteTopic(topicID, toTopicID):

    topicID = int(topicID)
    toTopicID = int(toTopicID)

    topicQuery = topics.topics.query.filter_by(id=topicID).first()

    channels = Channel.Channel.query.filter_by(topic=topicID).all()
    videos = RecordedVideo.RecordedVideo.query.filter_by(topic=topicID).all()

    newTopic = topics.topics.query.filter_by(id=toTopicID).first()

    for chan in channels:
        chan.topic = newTopic.id
    for vid in videos:
        vid.topic = newTopic.id

    system.newLog(
        1, "User " + current_user.username + " deleted Topic " + str(topicQuery.name)
    )
    db.session.delete(topicQuery)
    db.session.commit()
    cache.delete_memoized(cachedDbCalls.getAllTopics)

    # Initialize the Topic Cache
    topicQuery = cachedDbCalls.getAllTopics()
    for topic in topicQuery:
        globalvars.topicCache[topic.id] = topic.name

    return True
