import sys
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from flask import Blueprint
from flask_restplus import Api, Resource

import json

from classes import Channel
from classes import Stream
from classes import RecordedVideo
from classes import topics


blueprint = Blueprint('api', __name__, url_prefix='/api/1')
api = Api(blueprint, doc='/api/doc/')

### Start API Functions ###
@api.route('/channels/')
class api_1_ListChannels(Resource):
    def get(self):
        channelList = Channel.Channel.query.all()
        return json.dumps({'results': [ob.serialize() for ob in channelList]})

@api.route('/channels/<string:channelEndpointID>')
class api_1_ListChannel(Resource):
    def get(self, channelEndpointID):
        channelList = Channel.Channel.query.filter_by(channelLoc=channelEndpointID).all()
        return json.dumps({'results': [ob.serialize() for ob in channelList]})

@api.route('/streams')
class api_1_ListStreams(Resource):
    def get(self):
        streamList = Stream.Stream.query.all()
        return json.dumps({'results': [ob.serialize() for ob in streamList]})

@api.route('/streams/<int:streamID>')
class api_1_ListStream(Resource):
    def get(self, streamID):
        streamList = Stream.Stream.query.filter_by(id=streamID).all()
        return json.dumps({'results': [ob.serialize() for ob in streamList]})

@api.route('/vids')
class api_1_ListVideos(Resource):
    def get(self):
        videoList = RecordedVideo.RecordedVideo.query.all()
        return json.dumps({'results': [ob.serialize() for ob in videoList]})

@api.route('/vids/<int:videoID>')
class api_1_ListVideo(Resource):
    def get(self, videoID):
        videoList = RecordedVideo.RecordedVideo.query.filter_by(id=videoID).all()
        return json.dumps({'results': [ob.serialize() for ob in videoList]})

@api.route('/topics')
class api_1_ListTopics(Resource):
    def get(self):
        topicList = topics.topics.query.all()
        return json.dumps({'results': [ob.serialize() for ob in topicList]})

@api.route('/topics/<int:topicID>')
class api_1_ListTopic(Resource):
    def get(self, topicID):
        topicList = topics.topics.query.filter_by(id=topicID).all()
        return json.dumps({'results': [ob.serialize() for ob in topicList]})
