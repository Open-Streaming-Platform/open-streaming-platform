import sys
from os import path, remove
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from flask import Blueprint, request, url_for
from flask_restplus import Api, Resource, reqparse

import shutil
import uuid
import datetime
import socket

from classes import Sec
from classes import Channel
from classes import Stream
from classes import RecordedVideo
from classes import topics
from classes import upvotes
from classes import apikey
from classes import views
from classes import settings
from classes.shared import db

from functions import rtmpFunc

from globals import globalvars

def checkRTMPAuthIP(requestData):
    authorized = False
    requestIP = "0.0.0.0"
    if requestData.environ.get('HTTP_X_FORWARDED_FOR') is None:
        requestIP = requestData.environ['REMOTE_ADDR']
    else:
        requestIP = requestData.environ['HTTP_X_FORWARDED_FOR']

    authorizedRTMPServers = settings.rtmpServer.query.all()

    requestIP = requestIP.split(',')
    for ip in requestIP:
        parsedip = ip.strip()
        for server in authorizedRTMPServers:
            if authorized is False:
                if server.active is True:
                    resolveResults = socket.getaddrinfo(server.address, 0)
                    for resolved in resolveResults:
                        if parsedip == resolved[4][0]:
                            authorized = True
    print(requestIP)
    return (authorized, requestIP)

class fixedAPI(Api):
    # Monkeyfixed API IAW https://github.com/noirbizarre/flask-restplus/issues/223
    @property
    def specs_url(self):
        '''
        The Swagger specifications absolute url (ie. `swagger.json`)

        :rtype: str
        '''
        return url_for(self.endpoint('specs'), _external=False)

authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}

api_v1 = Blueprint('api', __name__, url_prefix='/apiv1')
api = fixedAPI(api_v1, version='1.0', title='OSP API', description='OSP API for Users, Streamers, and Admins', default='Primary', default_label='OSP Primary Endpoints', authorizations=authorizations)

### Start API Functions ###

channelParserPut = reqparse.RequestParser()
channelParserPut.add_argument('channelName', type=str)
channelParserPut.add_argument('description', type=str)
channelParserPut.add_argument('topicID', type=int)

channelParserPost = reqparse.RequestParser()
channelParserPost.add_argument('channelName', type=str, required=True)
channelParserPost.add_argument('description', type=str, required=True)
channelParserPost.add_argument('topicID', type=int, required=True)
channelParserPost.add_argument('recordEnabled', type=bool, required=True)
channelParserPost.add_argument('chatEnabled', type=bool, required=True)
channelParserPost.add_argument('commentsEnabled', type=bool, required=True)

streamParserPut = reqparse.RequestParser()
streamParserPut.add_argument('streamName', type=str)
streamParserPut.add_argument('topicID', type=int)

videoParserPut = reqparse.RequestParser()
videoParserPut.add_argument('videoName', type=str)
videoParserPut.add_argument('description', type=str)
videoParserPut.add_argument('topicID', type=int)

clipParserPut = reqparse.RequestParser()
clipParserPut.add_argument('clipName', type=str)
clipParserPut.add_argument('description', type=str)

xmppAuthParserPost = reqparse.RequestParser()
xmppAuthParserPost.add_argument('jid', type=str)
xmppAuthParserPost.add_argument('token', type=str)

xmppIsUserParserPost = reqparse.RequestParser()
xmppIsUserParserPost.add_argument('jid', type=str)

rtmpStage1Auth = reqparse.RequestParser()
rtmpStage1Auth.add_argument('name', type=str)
rtmpStage1Auth.add_argument('addr', type=str)

rtmpStage2Auth = reqparse.RequestParser()
rtmpStage2Auth.add_argument('name', type=str)
rtmpStage2Auth.add_argument('addr', type=str)

rtmpRecCheck = reqparse.RequestParser()
rtmpRecCheck.add_argument('name', type=str)

rtmpStreamClose = reqparse.RequestParser()
rtmpStreamClose.add_argument('name', type=str)
rtmpStreamClose.add_argument('addr', type=str)

rtmpRecClose = reqparse.RequestParser()
rtmpRecClose.add_argument('name', type=str)
rtmpRecClose.add_argument('path', type=str)

# TODO Add Clip Post Arguments

@api.route('/server')
class api_1_Server(Resource):
    # Server - Get Basic Server Information
    def get(self):
        """
            Displays a Listing of Server Settings
        """
        serverSettings = settings.settings.query.all()[0]
        db.session.commit()
        return {'results': serverSettings.serialize() }

@api.route('/server/edges')
class api_1_Edges(Resource):
    # Server - Get Edge Serves
    def get(self):
        """
            Displays a Listing of Edge Servers
        """

        edgeList = settings.edgeStreamer.query.all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in edgeList]}

@api.route('/channel/')
class api_1_ListChannels(Resource):
    # Channel - Get all Channels
    def get(self):
        """
            Gets a List of all Public Channels
        """
        channelList = Channel.Channel.query.all()
        db.session.commit()
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
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    args = channelParserPost.parse_args()
                    newChannel = Channel.Channel(int(requestAPIKey.userID), str(uuid.uuid4()), args['channelName'], int(args['topicID']), args['recordEnabled'], args['chatEnabled'], args['commentsEnabled'], args['description'])

                    userQuery = Sec.User.query.filter_by(id=int(requestAPIKey.userID)).first()

                    # Establish XMPP Channel
                    from app import ejabberd
                    sysSettings = settings.settings.query.all()[0]
                    ejabberd.create_room(newChannel.channelLoc, 'conference.' + sysSettings.siteAddress, sysSettings.siteAddress)
                    ejabberd.set_room_affiliation(newChannel.channelLoc, 'conference.' + sysSettings.siteAddress, int(requestAPIKey.userID) + "@" + sysSettings.siteAddress, "owner")

                    # Default values
                    for key, value in globalvars.room_config.items():
                        ejabberd.change_room_option(newChannel.channelLoc, 'conference.' + sysSettings.siteAddress, key, value)

                    # Name and title
                    ejabberd.change_room_option(newChannel.channelLoc, 'conference.' + sysSettings.siteAddress, 'title', newChannel.channelName)
                    ejabberd.change_room_option(newChannel.channelLoc, 'conference.' + sysSettings.siteAddress, 'description', userQuery.username + 's chat room for the channel "' + newChannel.channelName + '"')

                    db.session.add(newChannel)
                    db.session.commit()

                    return {'results': {'message':'Channel Created', 'apiKey':newChannel.streamKey}}, 200
        return {'results': {'message':"Request Error"}}, 400

@api.route('/channel/<string:channelEndpointID>')
@api.doc(params={'channelEndpointID': 'Channel Endpoint Descriptor, Expressed in a UUID Value(ex:db0fe456-7823-40e2-b40e-31147882138e)'})
class api_1_ListChannel(Resource):
    def get(self, channelEndpointID):
        """
            Get Info for One Channel
        """
        channelList = Channel.Channel.query.filter_by(channelLoc=channelEndpointID).all()
        db.session.commit()
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
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    channelQuery = Channel.Channel.query.filter_by(channelLoc=channelEndpointID, owningUser=requestAPIKey.userID).first()
                    if channelQuery is not None:
                        args = channelParserPut.parse_args()
                        if 'channelName' in args:
                            if args['channelName'] is not None:
                                channelQuery.channelName = args['channelName']
                        if 'description' in args:
                            if args['description'] is not None:
                                channelQuery.description = args['channelName']
                        if 'topicID' in args:
                            if args['topicID'] is not None:
                                possibleTopics = topics.topics.query.filter_by(id=int(args['topicID'])).first()
                                if possibleTopics is not None:
                                    channelQuery.topic = int(args['topicID'])
                        db.session.commit()
                        return {'results': {'message':'Channel Updated'}}, 200
        return {'results': {'message':'Request Error'}},400

    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def delete(self,channelEndpointID):
        """
            Deletes a Channel
        """
        if 'X-API-KEY' in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(key=request.headers['X-API-KEY']).first()
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    channelQuery = Channel.Channel.query.filter_by(channelLoc=channelEndpointID, owningUser=requestAPIKey.userID).first()
                    if channelQuery is not None:
                        videos_root = globalvars.videoRoot + 'videos/'
                        filePath = videos_root + channelQuery.channelLoc
                        if filePath != videos_root:
                            shutil.rmtree(filePath, ignore_errors=True)

                        channelVid = channelQuery.recordedVideo
                        channelUpvotes = channelQuery.upvotes
                        channelStreams = channelQuery.stream

                        for entry in channelVid:
                            for upvote in entry.upvotes:
                                db.session.delete(upvote)
                            vidComments = entry.comments
                            for comment in vidComments:
                                db.session.delete(comment)
                            vidViews = views.views.query.filter_by(viewType=1, itemID=entry.id)
                            for view in vidViews:
                                db.session.delete(view)
                            db.session.delete(entry)
                        for entry in channelUpvotes:
                            db.session.delete(entry)
                        for entry in channelStreams:
                            db.session.delete(entry)
                        db.session.delete(channelQuery)
                        db.session.commit()
                        return {'results': {'message': 'Channel Deleted'}}, 200
        return {'results': {'message': 'Request Error'}}, 400

# TODO Add Ability to Add/Delete/Change
@api.route('/channel/<string:channelEndpointID>/restreams')
@api.doc(security='apikey')
@api.doc(params={'channelEndpointID': 'GUID Channel Location'})
class api_1_GetRestreams(Resource):
    def get(self, channelEndpointID):
        """
             Returns all restream destinations for a channel
        """

        if 'X-API-KEY' in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(key=request.headers['X-API-KEY']).first()
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    channelData = Channel.Channel.query.filter_by(channelLoc=channelEndpointID, owningUser=requestAPIKey.userID).first()

        else:
            # Perform RTMP IP Authorization Check
            authorized = checkRTMPAuthIP(request)
            if authorized[0] is False:
                return {'results': {'message': "Unauthorized RTMP Server or Missing User API Key - " + authorized[1]}}, 400

            channelData = Channel.Channel.query.filter_by(channelLoc=channelEndpointID).first()

        if channelData is not None:
            restreamDestinations = channelData.restreamDestinations
            db.session.commit()
            return {'results': [ob.serialize() for ob in restreamDestinations]}

        else:
            db.session.commit()
            return {'results': {'message': 'Request Error'}}, 400

@api.route('/channel/authed/')
class api_1_ListChannelAuthed(Resource):
    # Channel - Get Authenticated View of a Single Channel
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def get(self):
        """
            Gets an authenticated view of the settings of all owned Channels
        """
        if 'X-API-KEY' in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(key=request.headers['X-API-KEY']).first()
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    channelQuery = Channel.Channel.query.filter_by(owningUser=requestAPIKey.userID).all()
                    if channelQuery != []:
                        db.session.commit()
                        return {'results': [ob.authed_serialize() for ob in channelQuery]}
        return {'results': {'message': 'Request Error'}}, 400


@api.route('/channel/authed/<string:channelEndpointID>')
@api.doc(params={'channelEndpointID': 'Channel Endpoint Descriptor, Expressed in a UUID Value(ex:db0fe456-7823-40e2-b40e-31147882138e)'})
class api_1_ListChannelAuthed(Resource):
    # Channel - Get Authenticated View of a Single Channel
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def get(self, channelEndpointID):
        """
            Gets an authenticated view of the settings of a Channel
        """
        if 'X-API-KEY' in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(key=request.headers['X-API-KEY']).first()
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    channelQuery = Channel.Channel.query.filter_by(channelLoc=channelEndpointID, owningUser=requestAPIKey.userID).all()
                    if channelQuery != []:
                        db.session.commit()
                        return {'results': [ob.authed_serialize() for ob in channelQuery]}
        return {'results': {'message': 'Request Error'}}, 400

@api.route('/stream/')
class api_1_ListStreams(Resource):
    def get(self):
        """
             Returns a List of All Active Streams
        """
        streamList = Stream.Stream.query.all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in streamList]}

@api.route('/stream/<int:streamID>')
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

    @api.expect(channelParserPut)
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

@api.route('/video/')
class api_1_ListVideos(Resource):
    def get(self):
        """
             Returns a List of All Recorded Videos
        """
        videoList = RecordedVideo.RecordedVideo.query.filter_by(pending=False, published=True).all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in videoList]}

@api.route('/video/<int:videoID>')
@api.doc(params={'videoID': 'ID Number for the Video'})
class api_1_ListVideo(Resource):
    def get(self, videoID):
        """
             Returns Info on a Single Recorded Video
        """
        videoList = RecordedVideo.RecordedVideo.query.filter_by(id=videoID, published=True).all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in videoList]}
    @api.expect(videoParserPut)
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def put(self, videoID):
        """
            Change a Video's Name, Description, or Topic
        """
        if 'X-API-KEY' in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(key=request.headers['X-API-KEY']).first()
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    videoQuery = RecordedVideo.RecordedVideo.query.filter_by(id=int(videoID)).first()
                    if videoQuery is not None:
                        if videoQuery.owningUser == requestAPIKey.userID:
                            args = videoParserPut.parse_args()
                            if 'videoName' in args:
                                if args['videoName'] is not None:
                                    videoQuery.channelName = args['videoName']
                            if 'topicID' in args:
                                if args['topicID'] is not None:
                                    possibleTopics = topics.topics.query.filter_by(id=int(args['topicID'])).first()
                                    if possibleTopics is not None:
                                        videoQuery.topic = int(args['topicID'])
                            if 'description' in args:
                                if args['description'] is not None:
                                    videoQuery.description = args['description']
                            db.session.commit()
                            return {'results': {'message': 'Video Updated'}}, 200
        return {'results': {'message': 'Request Error'}}, 400
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def delete(self,videoID):
        """
            Deletes a Video
        """
        if 'X-API-KEY' in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(key=request.headers['X-API-KEY']).first()
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    videoQuery = RecordedVideo.RecordedVideo.query.filter_by(id=videoID).first()
                    if videoQuery is not None:
                        if videoQuery.owningUser == requestAPIKey.userID:
                            videos_root = globalvars.videoRoot + 'videos/'

                            filePath = videos_root + videoQuery.videoLocation
                            thumbnailPath = videos_root + videoQuery.videoLocation[:-4] + ".png"

                            if filePath != videos_root:
                                if path.exists(filePath) and (
                                        videoQuery.videoLocation is not None or videoQuery.videoLocation != ""):
                                    remove(filePath)
                                    if path.exists(thumbnailPath):
                                        remove(thumbnailPath)
                            upvoteQuery = upvotes.videoUpvotes.query.filter_by(videoID=videoQuery.id).all()
                            for vote in upvoteQuery:
                                db.session.delete(vote)
                            vidComments = videoQuery.comments
                            for comment in vidComments:
                                db.session.delete(comment)
                            vidViews = views.views.query.filter_by(viewType=1, itemID=videoQuery.id)
                            for view in vidViews:
                                db.session.delete(view)
                            db.session.delete(videoQuery)
                            db.session.commit()
                            return {'results': {'message': 'Video Deleted'}}, 200
        return {'results': {'message': 'Request Error'}}, 400

@api.route('/clip/')
class api_1_ListClips(Resource):
    def get(self):
        """
             Returns a List of All Saved Clips
        """
        clipsList = RecordedVideo.Clips.query.filter_by(published=True).all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in clipsList]}

@api.route('/clip/<int:clipID>')
@api.doc(params={'clipID': 'ID Number for the Clip'})
class api_1_ListClip(Resource):
    def get(self, clipID):
        """
             Returns Info on a Single Saved Clip
        """
        clipList = RecordedVideo.Clips.query.filter_by(id=clipID, published=True).all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in clipList]}

    @api.expect(clipParserPut)
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def put(self, clipID):
        """
            Change a Clip's Name or Description
        """
        if 'X-API-KEY' in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(key=request.headers['X-API-KEY']).first()
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    clipQuery = RecordedVideo.Clips.query.filter_by(id=int(clipID)).first()
                    if clipQuery is not None:
                        if clipQuery.recordedVideo.owningUser == requestAPIKey.userID:
                            args = clipParserPut.parse_args()
                            if 'clipName' in args:
                                if args['clipName'] is not None:
                                    clipQuery.clipName = args['clipName']
                            if 'description' in args:
                                if args['description'] is not None:
                                    clipQuery.description = args['description']
                            db.session.commit()
                            return {'results': {'message': 'Clip Updated'}}, 200
        return {'results': {'message': 'Request Error'}}, 400

    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def delete(self, clipID):
        """
            Deletes a Clip
        """
        if 'X-API-KEY' in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(key=request.headers['X-API-KEY']).first()
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    clipQuery = RecordedVideo.Clips.query.filter_by(id=clipID).first()
                    if clipQuery is not None:
                        if clipQuery.owningUser == requestAPIKey.userID:
                            videos_root = globalvars.videoRoot + 'videos/'
                            thumbnailPath = videos_root + clipQuery.thumbnailLocation

                            if thumbnailPath != videos_root:
                                if path.exists(thumbnailPath) and clipQuery.thumbnailLocation is not None and clipQuery.thumbnailLocation != "":
                                    remove(thumbnailPath)
                            upvoteQuery = upvotes.clipUpvotes.query.filter_by(clipID=clipQuery.id).all()
                            for vote in upvoteQuery:
                                db.session.delete(vote)

                            db.session.delete(clipQuery)
                            db.session.commit()
                            return {'results': {'message': 'Clip Deleted'}}, 200
        return {'results': {'message': 'Request Error'}}, 400


@api.route('/topic/')
class api_1_ListTopics(Resource):
    def get(self):
        """
             Returns a List of All Topics
        """
        topicList = topics.topics.query.all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in topicList]}

@api.route('/topic/<int:topicID>')
@api.doc(params={'topicID': 'ID Number for Topic'})
class api_1_ListTopic(Resource):

    def get(self, topicID):
        """
             Returns Info on a Single Topic
        """
        topicList = topics.topics.query.filter_by(id=topicID).all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in topicList]}

@api.route('/user/<string:username>')
@api.doc(params={'username': 'Username of OSP User'})
class api_1_ListUser(Resource):
    def get(self, username):
        """
            Get Public Info for One User
        """
        userQuery = Sec.User.query.filter_by(username=username).all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in userQuery]}

@api.route('/xmpp/auth')
@api.doc(params={'jid': 'JID of user', 'token': 'Jabber Token'})
class api_1_xmppAuth(Resource):
    @api.expect(xmppAuthParserPost)
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def post(self):
        """
        Verify Chat Authentication
        """
        args = xmppAuthParserPost.parse_args()
        if 'jid' in args:
            jid = args['jid']
            if 'token' in args:
                token = args['token']
                sysSettings = settings.settings.query.first()
                if sysSettings is not None:
                    username = jid.replace("@" + sysSettings.siteAddress,"")
                    userQuery = Sec.User.query.filter_by(uuid=username, active=True).first()
                    if userQuery != None:
                        if userQuery.xmppToken == token:
                            return {'results': {'message': 'Successful Authentication', 'code': 200}}, 200
        return {'results': {'message': 'Request Error', 'code':400}}, 400

@api.route('/xmpp/isuser')
@api.doc(params={'jid': 'JID of user'})
class api_1_xmppisuser(Resource):
    @api.expect(xmppIsUserParserPost)
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def post(self):
        """
        Verify if User
        """
        args = xmppIsUserParserPost.parse_args()
        if 'jid' in args:
            jid = args['jid']
            sysSettings = settings.settings.query.first()
            if sysSettings is not None:
                username = jid.replace("@" + sysSettings.siteAddress,"")
                userQuery = Sec.User.query.filter_by(uuid=username).first()
                if userQuery != None:
                    return {'results': {'message': 'Successful Authentication', 'code': 200}}, 200
        return {'results': {'message': 'Request Error', 'code':400}}, 400

@api.route('/rtmp/stage1')
@api.doc(params={'name': 'Stream Key of Channel', 'addr':'IP Address of Endpoint Making Request'})
class api_1_rtmp_stage1(Resource):
    @api.expect(rtmpStage1Auth)
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def post(self):
        """
        Initialize Stage 1 of RTMP Authentication
        """
        # Perform RTMP IP Authorization Check
        authorized = checkRTMPAuthIP(request)
        if authorized[0] is False:
            return {'results': {'message':"Unauthorized RTMP Server - " + authorized[1]}}, 400

        args = rtmpStage1Auth.parse_args()

        if 'name' in args and 'addr' in args:
            name = args['name']
            addr = args['addr']
            results = rtmpFunc.rtmp_stage1_streamkey_check(name, addr)
            if results['success'] is True:
                return {'results': results}, 200
            else:
                return {'results': results}, 400
        else:
            return {'results': {'time': str(datetime.datetime.now()), 'request': 'Stage1', 'success': False, 'channelLoc': None, 'type': None, 'ipAddress': None, 'message': 'Invalid Request'}}, 400

@api.route('/rtmp/stage2')
@api.doc(params={'name': 'Channel Location of Channel Processed Under Stage 1', 'addr':'IP Address of Endpoint Making Request'})
class api_1_rtmp_stage2(Resource):
    @api.expect(rtmpStage2Auth)
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def post(self):
        """
        Initialize Stage 2 of RTMP Authentication
        """

        # Perform RTMP IP Authorization Check
        authorized = checkRTMPAuthIP(request)
        if authorized[0] is False:
            return {'results': {'message':"Unauthorized RTMP Server - " + authorized[1]}}, 400

        args = rtmpStage2Auth.parse_args()

        if 'name' in args and 'addr' in args:
            name = args['name']
            addr = args['addr']
            results = rtmpFunc.rtmp_stage2_user_auth_check(name, addr)
            if results['success'] is True:
                return {'results': results}, 200
            else:
                return {'results': results}, 400
        else:
            return {'results': {'time': str(datetime.datetime.now()), 'request': 'Stage2', 'success': False, 'channelLoc': None, 'type': None, 'ipAddress': None, 'message': 'Invalid Request'}}, 400

@api.route('/rtmp/reccheck')
@api.doc(params={'name': 'Stream Key of Channel'})
class api_1_rtmp_reccheck(Resource):
    @api.expect(rtmpRecCheck)
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def post(self):
        """
        Initialize Recording Check for RTMP
        """

        # Perform RTMP IP Authorization Check
        authorized = checkRTMPAuthIP(request)
        if authorized[0] is False:
            return {'results': {'message':"Unauthorized RTMP Server - " + authorized[1]}}, 400

        args = rtmpRecCheck.parse_args()

        if 'name' in args:
            name = args['name']
            results = rtmpFunc.rtmp_record_auth_check(name)
            if results['success'] is True:
                return {'results': results}, 200
            else:
                return {'results': results}, 400
        else:
            return {'results': {'time': str(datetime.datetime.now()), 'request': 'RecordCheck', 'success': False, 'channelLoc': None, 'type': None, 'ipAddress': None, 'message': 'Invalid Request'}}, 400

@api.route('/rtmp/streamclose')
@api.doc(params={'name': 'Stream Key of Channel', 'addr':'IP Address of Endpoint Making Request'})
class api_1_rtmp_streamclose(Resource):
    @api.expect(rtmpStreamClose)
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def post(self):
        """
        Close an Open Stream
        """

        # Perform RTMP IP Authorization Check
        authorized = checkRTMPAuthIP(request)
        if authorized[0] is False:
            return {'results': {'message':"Unauthorized RTMP Server -" + authorized[1]}}, 400

        args = rtmpStreamClose.parse_args()

        if 'name' in args and 'addr' in args:
            name = args['name']
            addr = args['addr']
            results = rtmpFunc.rtmp_user_deauth_check(name, addr)
            if results['success'] is True:
                return {'results': results}, 200
            else:
                return {'results': results}, 400
        else:
            return {'results': {'time': str(datetime.datetime.now()), 'request': 'StreamClose', 'success': False, 'channelLoc': None, 'type': None, 'ipAddress': None, 'message': 'Invalid Request'}}, 400

@api.route('/rtmp/recclose')
@api.doc(params={'name': 'Channel Location of Video to Close', 'path':'Nginx-rtmp Full Path of Preprocessed Video'})
class api_1_rtmp_recclose(Resource):
    @api.expect(rtmpRecClose)
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def post(self):
        """
        Finalize Processing of a Recorded Video
        """

        # Perform RTMP IP Authorization Check
        authorized = checkRTMPAuthIP(request)
        if authorized[0] is False:
            return {'results': {'message':"Unauthorized RTMP Server - " + authorized[1]}}, 400

        args = rtmpRecClose.parse_args()

        if 'name' in args and 'path' in args:
            name = args['name']
            path = args['path']
            results = rtmpFunc.rtmp_rec_Complete_handler(name, path)
            if results['success'] is True:
                return {'results': results}, 200
            else:
                return {'results': results}, 400
        else:
            return {'results': {'time': str(datetime.datetime.now()), 'request': 'RecordingClose', 'success': False, 'channelLoc': None, 'type': None, 'ipAddress': None, 'message': 'Invalid Request'}}, 400
