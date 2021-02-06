from flask_restplus import Api, Resource, reqparse, Namespace
from flask_security.utils import hash_password
from flask import request
import datetime
import uuid
import os
import re

from classes import Sec
from classes.shared import db

from app import user_datastore

from functions import apiFunc

api = Namespace('user', description='User Related Queries and Functions')

newUserPost = reqparse.RequestParser()
newUserPost.add_argument('username', type=str)
newUserPost.add_argument('email', type=str)
newUserPost.add_argument('password', type=str)

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

@api.route('/new')
class api_1_CreateUser(Resource):
    @api.expect(newUserPost)
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def post(self):
        """
            Create a New User - **Admin API Key Required**
        """
        if 'X-API-KEY' in request.headers:
            apiKey = request.headers['X-API-KEY']
            adminKeyCheck = apiFunc.isValidAdminKey(apiKey)
            if adminKeyCheck is True:
                args = newUserPost.parse_args()
                if 'username' in args and 'email' in args and 'password' in args:
                    username = args['username']
                    email = args['email']

                    # Email Address Validation
                    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                        return {'results': {'message': "Invalid Email Format"}}, 400

                    # Perform Existing Checks
                    existingUserQuery = Sec.User.query.filter_by(username=username).first()
                    if existingUserQuery != None:
                        return {'results': {'message': "Username already Exists"}}, 400
                    existingEmailQuery = Sec.User.query.filter_by(email=email).first()
                    if existingEmailQuery != None:
                        return {'results': {'message': "Email Address already Exists"}}, 400

                    password = hash_password(args['password'])
                    user_datastore.creatuser_datastore.create_user(email=email, username=username, password=password, active=True, confirmed_at=datetime.datetime.utcnow(), authType=0)
                    defaultRoleQuery = Sec.Role.query.filter_by(default=True).all()
                    newUserQuery = Sec.User.query.filter_by(email=email, username=username).first()
                    for role in defaultRoleQuery:
                        user_datastore.add_role_to_user(newUserQuery, role.name)
                    newUserQuery.authType = 0
                    newUserQuery.xmppToken = str(os.urandom(32).hex())
                    newUserQuery.uuid = str(uuid.uuid4())
                    db.session.commit()
                    return {'results': newUserQuery.serialize()}

        return {'results': {'message': "Request Error"}}, 400