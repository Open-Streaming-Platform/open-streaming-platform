import datetime

from flask_restplus import Api, Resource, reqparse, Namespace

from classes import settings
from classes.shared import db

api = Namespace('server', description='Server Related Queries and Functions')

@api.route('/')
class api_1_Server(Resource):
    # Server - Get Basic Server Information
    def get(self):
        """
            Displays a Listing of Server Settings
        """
        serverSettings = settings.settings.query.first()
        db.session.commit()
        return {'results': serverSettings.serialize()}


@api.route('/edges')
class api_1_Edges(Resource):
    # Server - Get Edge Serves
    def get(self):
        """
            Displays a Listing of Edge Servers
        """

        edgeList = settings.edgeStreamer.query.all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in edgeList]}

@api.route('/rtmp')
class api_1_Rtmp(Resource):
    # Server - Get RTMP Serves
    def get(self):
        """
            Displays a Listing of RTMP Servers
        """

        rtmpList = settings.rtmpServer.query.all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in rtmpList]}

@api.route('/ping')
class api_1_Ping(Resource):
    # Server - Returns Pong Check
    def get(self):
        """
            Returns a Server Pong
        """
        return {'results': {'message': 'Pong', 'timestamp': str(datetime.datetime.now())}}