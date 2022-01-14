import datetime

from flask_restplus import Api, Resource, reqparse, Namespace

from classes import settings
from classes.shared import db

from functions import cachedDbCalls


rtmpPost = reqparse.RequestParser()
rtmpPost.add_argument('address', type=str, required=True)
rtmpPort.add_argument('hide', type=bool, default=False)

rtmpDelete = reqparse.RequestParser()
rtmpDelete.add_argument('address', type=str, required=True)

api = Namespace('server', description='Server Related Queries and Functions')

@api.route('/')
class api_1_Server(Resource):
    # Server - Get Basic Server Information
    def get(self):
        """
            Displays a Listing of Server Settings
        """
        serverSettings = cachedDbCalls.getSystemSettings()
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

    @api.expect(rtmpPost)
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def post(self):
        """
            Adds a RTMP Server
        """

        if 'X-API-KEY' in request.headers:
            apiKey = request.headers['X-API-KEY']
            adminKeyCheck = apiFunc.isValidAdminKey(apiKey)
            if adminKeyCheck is True:
                args = rtmpPost.parse_args()
                newRTMP = settings.rtmpServer(args.address)
                newRTMP.hide = args.hide
                db.session.add(newRTMP)
                db.session.commit()
                return {'results': {'message': 'RTMP Server Created'}}
            else:
                return {'results': {'message': "Unauthorized"}}, 401
        else:
            return {'results': {'message': "Request Error"}}, 400

    @api.expect(rtmpDelete)
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def delete(self):
        """
            Deletes a RTMP Server
        """

        if 'X-API-KEY' in request.headers:
            apiKey = request.headers['X-API-KEY']
            adminKeyCheck = apiFunc.isValidAdminKey(apiKey)
            if adminKeyCheck is True:
                args = rtmpPost.parse_args()
                rtmpQuery = settings.rtmpServer.query.filter_by(address=args.address).first()
                if rtmpQuery is not None:
                    db.session.delete(rtmpQuery)
                    db.session.commit()
                    return {'results': {'message': 'RTMP Server Removed'}}
                else:
                    db.session.commit()
                    return {'results': {'message': 'No Such RTMP Server'}}
            else:
                return {'results': {'message': "Unauthorized"}}, 401
        else:
            return {'results': {'message': "Request Error"}}, 400

@api.route('/ping')
class api_1_Ping(Resource):
    # Server - Returns Pong Check
    def get(self):
        """
            Returns a Server Pong
        """
        return {'results': {'message': 'Pong', 'timestamp': str(datetime.datetime.now())}}