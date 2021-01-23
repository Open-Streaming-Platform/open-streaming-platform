from flask_restplus import Api, Resource, reqparse, Namespace

from classes import Sec
from classes.shared import db

api = Namespace('user', description='User Related Queries and Functions')

@api.route('/<string:username>')
@api.doc(params={'username': 'Username of OSP User'})
class api_1_ListUser(Resource):
    def get(self, username):
        """
            Get Public Info for One User
        """
        userQuery = Sec.User.query.filter_by(username=username).all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in userQuery]}