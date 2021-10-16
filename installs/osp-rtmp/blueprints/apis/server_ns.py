import datetime

from flask_restplus import Api, Resource, reqparse, Namespace

api = Namespace('server', description='Server Related Queries and Functions')

@api.route('/ping')
class api_1_ping(Resource):
    # Ping - Get Basic Server Information
    def get(self):
        """
            Displays basic ping/pong response
        """
        return {'results': { "message": "pong" } }