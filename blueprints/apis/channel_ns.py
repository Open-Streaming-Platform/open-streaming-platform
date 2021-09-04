from flask_restplus import Api, Resource, reqparse, Namespace
from flask import request

import uuid
import shutil
import socket

from classes import settings
from classes import Channel
from classes import apikey
from classes import Sec
from classes import topics
from classes import views
from classes.shared import db

from functions import system

from globals import globalvars

api = Namespace('channel', description='Channels Related Queries and Functions')

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

def checkRTMPAuthIP(requestData):
    authorized = False
    requestIP = "0.0.0.0"
    if requestData.environ.get('HTTP_X_FORWARDED_FOR') is None:
        requestIP = requestData.environ['REMOTE_ADDR']
    else:
        requestIP = requestData.environ['HTTP_X_FORWARDED_FOR']

    authorizedRTMPServers = settings.rtmpServer.query.all()

    receivedIP = requestIP
    ipList = requestIP.split(',')
    confirmedIP = ""
    for ip in ipList:
        parsedip = ip.strip()
        for server in authorizedRTMPServers:
            if authorized is False:
                if server.active is True:
                    resolveResults = socket.getaddrinfo(server.address, 0)
                    for resolved in resolveResults:
                        if parsedip == resolved[4][0]:
                            authorized = True
                            confirmedIP = resolved[4][0]

    if authorized is False:
        confirmedIP = receivedIP
        system.newLog(1, "Unauthorized RTMP Server - " + confirmedIP)

    return (authorized, confirmedIP)


@api.route('/')
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
                    ejabberd.set_room_affiliation(newChannel.channelLoc, 'conference.' + sysSettings.siteAddress, str(userQuery.uuid) + "@" + sysSettings.siteAddress, "owner")

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


@api.route('/<string:channelEndpointID>')
@api.doc(security='apikey')
@api.doc(params={'channelEndpointID': 'Channel Endpoint Descriptor, Expressed in a UUID Value(ex:db0fe456-7823-40e2-b40e-31147882138e)'})
class api_1_ListChannel(Resource):
    def get(self, channelEndpointID):
        """
            Get Info for One Channel
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
        else:
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
                        return {'results': {'message': 'Channel Updated'}}, 200
        return {'results': {'message': 'Request Error'}},400

    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def delete(self, channelEndpointID):
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

                        videoQuery = channelQuery.recordedVideo
                        channelUpvotes = channelQuery.upvotes
                        channelStreams = channelQuery.stream

                        for video in videoQuery:
                            video.remove()
                            for clip in video.clips:
                                for upvotes in clip:
                                    db.session.delete(upvotes)
                                clip.remove()
                                db.session.delete(clip)
                            for upvote in video.upvotes:
                                db.session.delete(upvote)
                            for comment in video.comments:
                                db.session.delete(comment)
                            vidViews = views.views.query.filter_by(viewType=1, itemID=video.id).all()
                            for view in vidViews:
                                db.session.delete(view)
                            db.session.delete(video)
                        for entry in channelUpvotes:
                            db.session.delete(entry)
                        for entry in channelStreams:
                            db.session.delete(entry)
                        db.session.delete(channelQuery)
                        db.session.commit()
                        return {'results': {'message': 'Channel Deleted'}}, 200
        return {'results': {'message': 'Request Error'}}, 400


# TODO Add Ability to Add/Delete/Change
@api.route('/<string:channelEndpointID>/restreams')
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


@api.route('/authed/')
class api_1_ListChannelAuthed(Resource):
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
