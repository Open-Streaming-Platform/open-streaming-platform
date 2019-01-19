import sys
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from flask import Blueprint, request
from flask_restplus import Api, Resource, reqparse

import uuid

from classes import Channel
from classes import Stream
from classes import RecordedVideo
from classes import topics
from classes import apikey
from classes.shared import db


authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}

api_v1 = Blueprint('api', __name__, url_prefix='/apiv1')
api = Api(api_v1, version='1.0', title='OSP API', description='OSP API for Users, Streamers, and Admins', authorizations=authorizations)

### Start API Functions ###

channelParserPut = reqparse.RequestParser()
channelParserPut.add_argument('channelName', type=str)
channelParserPut.add_argument('topicID', type=int)

channelParserPost = reqparse.RequestParser()
channelParserPost.add_argument('channelName', type=str, required=True)
channelParserPost.add_argument('topicID', type=int, required=True)
channelParserPost.add_argument('recordEnabled', type=bool, required=True)
channelParserPost.add_argument('chatEnabled', type=bool, required=True)

@api.route('/channels/')
class api_1_ListChannels(Resource):
    # Channel - Get all Channels
    def get(self):
        """
            Gets a List of all Public Channels
        """
        channelList = Channel.Channel.query.all()
        return {'results': [ob.serialize() for ob in channelList]}
    # Channel - Create Channel
    @api.expect(channelParserPost)
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def post(self):
        """
            Creates a New Channel
        """
        if 'X-API-KEY' in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(key=request.headers['X-API-KEY']).first()
            if requestAPIKey != None:
                args = channelParserPost.parse_args()
                newChannel = Channel.Channel(int(requestAPIKey.userID),str(uuid.uuid4()),args['channelName'],int(args['topicID']),args['recordEnabled'],args['chatEnabled'])
                db.session.add(newChannel)
                db.session.commit()

                return {'results': {'message':'Channel Created', 'apiKey':newChannel.streamKey}}, 200
        return {'results': {'message':"Request Error"}}, 400


@api.route('/channels/<string:channelEndpointID>')
@api.doc(params={'channelEndpointID': 'Channel Endpoint Descriptor, Expressed in a UUID Value(ex:db0fe456-7823-40e2-b40e-31147882138e)'})
class api_1_ListChannel(Resource):
    def get(self, channelEndpointID):
        """
            Get Info for One Channel
        """
        channelList = Channel.Channel.query.filter_by(channelLoc=channelEndpointID).all()
        return {'results': [ob.serialize() for ob in channelList]}
    # Channel - Change Channel Name or Topic ID
    @api.expect(channelParserPut)
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def put(self, channelEndpointID):
        """
            Change a Channel's Name or Topic
        """
        if 'X-API-KEY' in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(key=request.headers['X-API-KEY']).first()
            if requestAPIKey != None:
                channelQuery = Channel.Channel.query.filter_by(channelLoc=channelEndpointID, owningUser=requestAPIKey.userID).first()
                if channelQuery != None:
                    args = channelParserPut.parse_args()
                    if 'channelName' in args:
                        if args['channelName'] is not None:
                            channelQuery.channelName = args['channelName']
                    if 'topicID' in args:
                        if args['topicID'] is not None:
                            possibleTopics = topics.topics.query.filter_by(id=int(args['topicID'])).first()
                            if possibleTopics != None:
                                channelQuery.topic = int(args['topicID'])
                    db.session.commit()
                    return {'results': {'message':'Channel Updated'}}, 200
        else:
            return {'results': {'message':'Request Error'}},

@api.route('/streams/')
class api_1_ListStreams(Resource):
    def get(self):
        """
             Returns a List of All Active Streams
        """
        streamList = Stream.Stream.query.all()
        return {'results': [ob.serialize() for ob in streamList]}

@api.route('/streams/<int:streamID>')
@api.doc(params={'streamID': 'ID Number for the Stream'})
class api_1_ListStream(Resource):
    def get(self, streamID):
        """
             Returns Info on a Single Active Streams
        """
        streamList = Stream.Stream.query.filter_by(id=streamID).all()
        return {'results': [ob.serialize() for ob in streamList]}

@api.route('/vids/')
class api_1_ListVideos(Resource):
    def get(self):
        """
             Returns a List of All Recorded Videos
        """
        videoList = RecordedVideo.RecordedVideo.query.filter_by(pending=False).all()
        return {'results': [ob.serialize() for ob in videoList]}

@api.route('/vids/<int:videoID>')
@api.doc(params={'videoID': 'ID Number for the Video'})
class api_1_ListVideo(Resource):
    def get(self, videoID):
        """
             Returns Info on a Single Recorded Video
        """
        videoList = RecordedVideo.RecordedVideo.query.filter_by(id=videoID).all()
        return {'results': [ob.serialize() for ob in videoList]}

@api.route('/topics/')
class api_1_ListTopics(Resource):
    def get(self):
        """
             Returns a List of All Topics
        """
        topicList = topics.topics.query.all()
        return {'results': [ob.serialize() for ob in topicList]}

@api.route('/topics/<int:topicID>')
@api.doc(params={'topicID': 'ID Number for Topic'})
class api_1_ListTopic(Resource):
    def get(self, topicID):
        """
             Returns Info on a Single Topic
        """
        topicList = topics.topics.query.filter_by(id=topicID).all()
        return {'results': [ob.serialize() for ob in topicList]}
