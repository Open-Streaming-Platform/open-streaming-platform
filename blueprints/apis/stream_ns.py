from flask_restplus import Api, Resource, reqparse, Namespace
from flask import request

from classes import Stream
from classes import apikey
from classes import topics
from classes.shared import db

api = Namespace('stream', description='Stream Related Queries and Functions')

streamParserPut = reqparse.RequestParser()
streamParserPut.add_argument('streamName', type=str)
streamParserPut.add_argument('topicID', type=int)


@api.route('/')
class api_1_ListStreams(Resource):
    def get(self):
        """
             Returns a List of All Active Streams
        """
        streamList = Stream.Stream.query.all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in streamList]}


@api.route('/<int:streamID>')
@api.doc(params={'streamID': 'ID Number for the Stream'})
class api_1_ListStream(Resource):
    def get(self, streamID):
        """
             Returns Info on a Single Active Streams
        """
        streamList = Stream.Stream.query.filter_by(id=streamID).all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in streamList]}
        # Channel - Change Channel Name or Topic ID

    @api.expect(streamParserPut)
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def put(self, streamID):
        """
            Change a Streams's Name or Topic
        """
        if 'X-API-KEY' in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(key=request.headers['X-API-KEY']).first()
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    streamQuery = Stream.Stream.query.filter_by(id=int(streamID)).first()
                    if streamQuery is not None:
                        if streamQuery.channel.owningUser == requestAPIKey.userID:
                            args = streamParserPut.parse_args()
                            if 'streamName' in args:
                                if args['streamName'] is not None:
                                    streamQuery.streamName = args['streamName']
                            if 'topicID' in args:
                                if args['topicID'] is not None:
                                    possibleTopics = topics.topics.query.filter_by(id=int(args['topicID'])).first()
                                    if possibleTopics is not None:
                                        streamQuery.topic = int(args['topicID'])
                            db.session.commit()
                            return {'results': {'message': 'Stream Updated'}}, 200
        return {'results': {'message': 'Request Error'}}, 400