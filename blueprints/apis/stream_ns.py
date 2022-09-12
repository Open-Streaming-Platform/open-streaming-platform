from flask_restx import Api, Resource, reqparse, Namespace
from flask import request

from classes import Stream
from classes import apikey
from classes import topics
from classes import settings
from classes import upvotes
from classes.shared import db

from functions import cachedDbCalls

api = Namespace("stream", description="Stream Related Queries and Functions")

streamParserPut = reqparse.RequestParser()
streamParserPut.add_argument("streamName", type=str)
streamParserPut.add_argument("topicID", type=int)

streamSearchPost = reqparse.RequestParser()
streamSearchPost.add_argument("term", type=str)


@api.route("/")
class api_1_ListStreams(Resource):
    def get(self):
        """
        Returns a List of All Active Streams
        """
        results = []
        sysSettings = cachedDbCalls.getSystemSettings()

        streamList = (
            Stream.Stream.query.filter_by(active=True)
            .with_entities(
                Stream.Stream.id,
                Stream.Stream.uuid,
                Stream.Stream.startTimestamp,
                Stream.Stream.linkedChannel,
                Stream.Stream.streamName,
                Stream.Stream.topic,
                Stream.Stream.currentViewers,
                Stream.Stream.active,
                Stream.Stream.rtmpServer,
            )
            .all()
        )
        for stream in streamList:
            channelQuery = cachedDbCalls.getChannel(stream.linkedChannel)
            if channelQuery.private != True:
                rtmpQuery = settings.rtmpServer.query.filter_by(
                    id=stream.rtmpServer
                ).first()
                upvotesQueryCount = upvotes.streamUpvotes.query.filter_by(
                    streamID=stream.id
                ).count()

                streamURL = ""
                if sysSettings.adaptiveStreaming is True:
                    streamURL = "/live-adapt/" + channelQuery.channelLoc + ".m3u8"
                else:
                    streamURL = "/live/" + channelQuery.channelLoc + "/index.m3u8"

                entry = {
                    "id": stream.id,
                    "uuid": stream.uuid,
                    "startTimestamp": str(stream.startTimestamp),
                    "channelID": stream.linkedChannel,
                    "channelEndpointID": channelQuery.channelLoc,
                    "owningUser": channelQuery.owningUser,
                    "streamPage": "/view/" + channelQuery.channelLoc + "/",
                    "streamURL": streamURL,
                    "streamName": stream.streamName,
                    "thumbnail": "/stream-thumb/" + channelQuery.channelLoc + ".png",
                    "gifLocation": "/stream-thumb/" + channelQuery.channelLoc + ".gif",
                    "topic": stream.topic,
                    "rtmpServer": rtmpQuery.address,
                    "currentViewers": stream.currentViewers,
                    "totalViewers": stream.currentViewers,
                    "active": stream.active,
                    "upvotes": upvotesQueryCount,
                }
                results.append(entry)

        db.session.commit()
        return {"results": results}


@api.route("/<int:streamID>")
@api.doc(params={"streamID": "ID Number for the Stream"})
class api_1_ListStream(Resource):
    def get(self, streamID):
        """
        Returns Info on a Single Active Streams
        """
        streamList = Stream.Stream.query.filter_by(active=True, id=streamID).all()
        db.session.commit()
        return {"results": [ob.serialize() for ob in streamList]}
        # Channel - Change Channel Name or Topic ID

    @api.expect(streamParserPut)
    @api.doc(security="apikey")
    @api.doc(responses={200: "Success", 400: "Request Error"})
    def put(self, streamID):
        """
        Change a Streams's Name or Topic
        """
        if "X-API-KEY" in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(
                key=request.headers["X-API-KEY"]
            ).first()
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    streamQuery = Stream.Stream.query.filter_by(
                        active=True, id=int(streamID)
                    ).first()
                    if streamQuery is not None:
                        channelQuery = cachedDbCalls.getChannel(
                            streamQuery.linkedChannel
                        )
                        if channelQuery.owningUser == requestAPIKey.userID:
                            args = streamParserPut.parse_args()
                            if "streamName" in args:
                                if args["streamName"] is not None:
                                    streamQuery.streamName = args["streamName"]
                            if "topicID" in args:
                                if args["topicID"] is not None:
                                    possibleTopics = topics.topics.query.filter_by(
                                        id=int(args["topicID"])
                                    ).first()
                                    if possibleTopics is not None:
                                        streamQuery.topic = int(args["topicID"])
                            db.session.commit()
                            return {"results": {"message": "Stream Updated"}}, 200
        return {"results": {"message": "Request Error"}}, 400


@api.route("/search")
class api_1_SearchStreams(Resource):
    # Streams - Search Live Streams
    @api.expect(streamSearchPost)
    @api.doc(responses={200: "Success", 400: "Request Error"})
    def post(self):
        """
        Searches Stream Names and Metadata and returns Name and Link
        """
        sysSettings = cachedDbCalls.getSystemSettings()
        args = streamSearchPost.parse_args()
        returnArray = []
        if "term" in args:
            returnArray = cachedDbCalls.searchStreams(args["term"])
            return {"results": returnArray, "adaptive": sysSettings.adaptiveStreaming}
        else:
            return {"results": {"message": "Request Error"}}, 400
