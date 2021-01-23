from flask_restplus import Api, Resource, reqparse, Namespace
from flask import request
import datetime
import socket

from classes import settings
from classes.shared import db

from functions import rtmpFunc
from functions import system

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

api = Namespace('rtmp', description='RTMP Related Queries and Functions')

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

@api.route('/stage1')
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


@api.route('/stage2')
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


@api.route('/reccheck')
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


@api.route('/streamclose')
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


@api.route('/recclose')
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