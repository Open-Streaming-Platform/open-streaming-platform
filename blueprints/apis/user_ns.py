from flask_restx import Api, Resource, reqparse, Namespace
from flask_security.utils import hash_password
from flask import request
import datetime
import uuid
import os
import re

from globals import globalvars

from classes import Sec, Channel, RecordedVideo, views, upvotes
from classes.shared import db

from app import user_datastore

from functions import apiFunc, cachedDbCalls, securityFunc

api = Namespace('user', description='User Related Queries and Functions')

getUser = reqparse.RequestParser()
getUser.add_argument('username', type=str)

newUserPost = reqparse.RequestParser()
newUserPost.add_argument('username', type=str, required=True)
newUserPost.add_argument('email', type=str, required=True)
newUserPost.add_argument('password', type=str, required=True)

deleteUser = reqparse.RequestParser()
deleteUser.add_argument('username', type=str, required=True)

roleArgs = reqparse.RequestParser()
roleArgs.add_argument('username', type=str, required=True)
roleArgs.add_argument('role', type=str, required=True)

userSearchPost = reqparse.RequestParser()
userSearchPost.add_argument('term', type=str, required=True)

@api.route('/')
class api_1_AdminUser(Resource):
    @api.expect(getUser)
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def get(self):
        """
            Get User Info
        """
        if 'X-API-KEY' in request.headers:
            apiKey = request.headers['X-API-KEY']
            adminKeyCheck = apiFunc.isValidAdminKey(apiKey)
            if adminKeyCheck is True:
                args = getUser.parse_args()
                if 'username' in args:
                    username = args['username']
                    userQuery = Sec.User.query.filter_by(username=username).all()
                    db.session.commit()
                    return {'results': [ob.serialize() for ob in userQuery]}
                else:
                    userQuery = Sec.User.query.all()
                    db.session.commit()
                    return {'results': [ob.serialize() for ob in userQuery]}
        else:
            args = getUser.parse_args()
            if 'username' in args:
                username = args['username']
                userQuery = Sec.User.query.filter_by(username=username).all()
                db.session.commit()
                return {'results': [ob.serialize() for ob in userQuery]}
            else:
                return {'results': {'message': "Request Error"}}, 400

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
                        db.session.commit()
                        return {'results': {'message': "Invalid Email Format"}}, 400

                    # Perform Existing Checks
                    existingUserQuery = Sec.User.query.filter_by(username=username).first()
                    if existingUserQuery != None:
                        db.session.commit()
                        return {'results': {'message': "Username already Exists"}}, 400
                    existingEmailQuery = Sec.User.query.filter_by(email=email).first()
                    if existingEmailQuery != None:
                        db.session.commit()
                        return {'results': {'message': "Email Address already Exists"}}, 400

                    password = hash_password(args['password'])
                    user_datastore.create_user(email=email, username=username, password=password, active=True, confirmed_at=datetime.datetime.utcnow(), authType=0)
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

    @api.expect(deleteUser)
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def delete(self):
        """
        Delete a User - **Admin API Key Required**
        """
        if 'X-API-KEY' in request.headers:
            apiKey = request.headers['X-API-KEY']
            adminKeyCheck = apiFunc.isValidAdminKey(apiKey)
            if adminKeyCheck is True:
                args = deleteUser.parse_args()
                if 'username' in args:
                    username = args['username']
                    userQuery = Sec.User.query.filter_by(username=username).first()
                    if userQuery is not None:
                        securityFunc.delete_user(userQuery.id)
                        return {'results': {'message': 'User ' + username +' deleted'}}
                    else:
                        db.session.commit()
                        return {'results': {'message': "No Such Username"}}, 400
        return {'results': {'message': "Request Error"}}, 400

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

@api.route('/role')
@api.doc(params={'username': 'Username of OSP User', 'role': 'Role being added or deleted. (Admin, User, Streamer, Recorder, Uploader)'})
class api_1_RoleMgmt(Resource):
    @api.expect(roleArgs)
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def post(self):
        """
            Add a role to a user - **Admin API Key Required**
        """
        if 'X-API-KEY' in request.headers:
            apiKey = request.headers['X-API-KEY']
            adminKeyCheck = apiFunc.isValidAdminKey(apiKey)
            if adminKeyCheck is True:
                args = roleArgs.parse_args()
                if 'username' and 'role' in args:
                    username = args['username']
                    role = (args['role']).title()
                    userQuery = Sec.User.query.filter_by(username=username).first()
                    if userQuery is not None:
                        roleQuery = Sec.Role.query.filter_by(name=role).first()
                        if roleQuery is not None:
                            user_datastore.add_role_to_user(userQuery, roleQuery)
                            db.session.commit()
                            return {'results': {'message': 'Role ' + role + ' added to ' + username}}
                        else:
                            db.session.commit()
                            return {'results': {'message': "No Such Role"}}, 400
                    else:
                        db.session.commit()
                        return {'results': {'message': "No Such Username"}}, 400
        db.session.commit()
        return {'results': {'message': "Request Error"}}, 400

    @api.expect(roleArgs)
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def delete(self):
        """
            Remove a role from a user - **Admin API Key Required**
        """
        if 'X-API-KEY' in request.headers:
            apiKey = request.headers['X-API-KEY']
            adminKeyCheck = apiFunc.isValidAdminKey(apiKey)
            if adminKeyCheck is True:
                args = roleArgs.parse_args()
                if 'username' and 'role' in args:
                    username = args['username']
                    role = (args['role']).title()
                    userQuery = Sec.User.query.filter_by(username=username).first()
                    if userQuery is not None:
                        roleQuery = Sec.Role.query.filter_by(name=role).first()
                        if roleQuery is not None:
                            user_datastore.remove_role_from_user(userQuery, roleQuery)
                            db.session.commit()
                            return {'results': {'message': 'Role ' + role + ' removed from ' + username}}
                        else:
                            db.session.commit()
                            return {'results': {'message': "No Such Role"}}, 400
                    else:
                        db.session.commit()
                        return {'results': {'message': "No Such Username"}}, 400
        db.session.commit()
        return {'results': {'message': "Request Error"}}, 400

@api.route('/search')
class api_1_SearchUsers(Resource):
    # Users - Search Users
    @api.expect(userSearchPost)
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def post(self):
        """
            Searches User Names and Metadata and returns Name and Link
        """
        args = userSearchPost.parse_args()
        returnArray = []
        if 'term' in args:
            returnArray = cachedDbCalls.searchUsers(args['term'])
            return {'results': returnArray}
        else:
            return {'results': {'message': 'Request Error'}}, 400