def prepareHubJSON():
    topicQuery = topics.topics.query.all()
    topicDump = {}
    for topic in topicQuery:
        topicDump[topic.id] = {"name": topic.name, "img": topic.iconClass}

    streamerIDs = []
    for channel in db.session.query(Channel.Channel.owningUser).distinct():
        if channel.owningUser not in streamerIDs:
            streamerIDs.append(channel.owningUser)

    streamerDump = {}
    for streamerID in streamerIDs:
        streamerQuery = Sec.User.query.filter_by(id=streamerID).first()
        streamerDump[streamerQuery.id] = {"username": streamerQuery.username, "biography": streamerQuery.biography,
                                          "img": streamerQuery.pictureLocation, "location": "/streamers/" + str(streamerQuery.id) + "/"}

    channelDump = {}
    channelQuery = Channel.Channel.query.all()
    for channel in channelQuery:
        channelDump[channel.id] = {"streamer": channel.owningUser, "name": channel.channelName,
                                   "location": "/channel/link/" + channel.channelLoc, "topic": channel.topic, "views": channel.views,
                                   "protected": channel.protected,
                                   "currentViewers": channel.currentViewers, "img": channel.imageLocation,
                                   "description": channel.description}

    videoDump = {}
    videoQuery = RecordedVideo.RecordedVideo.query.filter_by(pending=False).all()
    for video in videoQuery:
        videoDump[video.id] = {"streamer": video.owningUser, "name": video.channelName, "channelID": video.channelID,
                               "description": video.description, "topic": video.topic, "views": video.views,
                               "length": video.length, "location": "/play/" + str(video.id), "img": video.thumbnailLocation, "upvotes": str(votes.get_Video_Upvotes(video.id))}

    clipDump = {}
    clipQuery = RecordedVideo.Clips.query.all()
    for clip in clipQuery:
        clipDump[clip.id] = {"parentVideo": clip.parentVideo, "length": clip.length, "views": clip.views,
                             "name": clip.clipName, "description": clip.description, "img": clip.thumbnailLocation, "location": "/clip/" + str(clip.id), "upvotes": str(votes.get_Clip_Upvotes(clip.id))}

    streamDump = {}
    streamQuery = Stream.Stream.query.all()
    for stream in streamQuery:
        streamDump[stream.id] = {"channelID": stream.linkedChannel, "location": ("/view/" + stream.channel.channelLoc + "/"), "streamer": str(stream.channel.owningUser),
                                 "name": stream.streamName, "topic": stream.topic, "currentViewers": stream.currentViewers, "views": stream.totalViewers,
                                 "img": stream.channel.channelLoc + ".png", "upvotes": str(votes.get_Stream_Upvotes(stream.id))}

    dataDump = {"topics": topicDump, "streamers": streamerDump, "channels": channelDump, "videos": videoDump,
                "clips": clipDump, "streams": streamDump}
    db.session.close()
    return dataDump

def processHubConnection(connection, payload):
    hubServer = connection.server
    apiEndpoint = "apiv1"

    r = None
    try:
        r = requests.post(hubServer.serverAddress + '/' + apiEndpoint + '/update', data={'serverToken': connection.serverToken, 'jsonData': json.dumps(payload)})
    except requests.exceptions.Timeout:
        newLog(10, "Failed Update to OSP Hub Due to Timeout - Server:" + str(hubServer.serverAddress))
        return False
    except requests.exceptions.ConnectionError:
        newLog(10, "Failed Update to OSP Hub Due to Connection Error - Server:" + str(hubServer.serverAddress))
        return False
    if r.status_code == 200:
        connection.lastUpload = datetime.datetime.now()
        db.session.commit()
        db.session.close()
        newLog(10,"Successful Update to OSP Hub - Server:" + str(hubServer.serverAddress))
        return True
    else:
        newLog(10, "Failed Update to OSP Hub Due to Error " + str(r.status_code) + " - Server:" + str(hubServer.serverAddress))
    return False

#def processAllHubConnections():
#    jsonPayload = prepareHubJSON()
#
#    results = []
#
#    hubConnectionQuery = hubConnection.hubConnection.query.filter_by(status=1).all()
#    for connection in hubConnectionQuery:
#        results.append(processHubConnection(connection, jsonPayload))
#    return results