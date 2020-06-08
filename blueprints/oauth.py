import datetime
import random
import uuid
import os

from flask import redirect, url_for, Blueprint, flash, render_template, request, abort
from flask_security.utils import login_user
from flask_security.utils import verify_password

from classes import settings
from classes import Sec
from classes.shared import oauth, db

import json

from time import time

from app import user_datastore
from functions.oauth import fetch_token, discord_processLogin, reddit_processLogin, facebook_processLogin
from functions.system import newLog
from functions.webhookFunc import runWebhook
from functions.themes import checkOverride

oauth_bp = Blueprint('oauth', __name__, url_prefix='/oauth')

@oauth_bp.route('/login/<provider>')
def oAuthLogin(provider):
    sysSettings = settings.settings.query.first()
    if sysSettings is not None:

        oAuthClient = oauth.create_client(provider)
        redirect_url = sysSettings.siteProtocol + sysSettings.siteAddress + '/oauth/authorize/' + provider
        return oAuthClient.authorize_redirect(redirect_url)
    else:
        redirect(url_for('root.main_page'))

@oauth_bp.route('/authorize/<provider>')
def oAuthAuthorize(provider):
    oAuthClient = oauth.create_client(provider)
    oAuthProviderQuery = settings.oAuthProvider.query.filter_by(name=provider).first()
    if oAuthProviderQuery is not None:

        try:
            token = oAuthClient.authorize_access_token()
        except:
            return redirect('/login')

        userData = oAuthClient.get(oAuthProviderQuery.profile_endpoint)
        userDataDict = userData.json()

        userQuery = Sec.User.query.filter_by(oAuthID=userDataDict[oAuthProviderQuery.id_value], oAuthProvider=provider, authType=1).first()

        # Default expiration time to 365 days into the future
        if 'expires_at' not in token:
            if 'expires_in' in token:
                token['expires_at'] = datetime.timedelta(seconds=int(token['exipires_in'])) + datetime.datetime.now()
            else:
                token['expires_at'] = time() + (365 * 24 * 3600)

        # If oAuth ID, Provider, and Auth Type Match - Initiate Login
        if userQuery is not None:
            existingTokenQuery = Sec.OAuth2Token.query.filter_by(user=userQuery.id).all()
            for existingToken in existingTokenQuery:
                db.session.delete(existingToken)
            db.session.commit()
            newToken = None
            if 'refresh_token' in token:
                newToken = Sec.OAuth2Token(provider, token['token_type'], token['access_token'], token['refresh_token'], token['expires_at'], userQuery.id)
            else:
                newToken = Sec.OAuth2Token(provider, token['token_type'], token['access_token'], None, token['expires_at'], userQuery.id)
            db.session.add(newToken)
            db.session.commit()

            if userQuery.active is False:
                flash("User has been Disabled.  Please contact your administrator","error")
                return redirect('/login')
            else:
                login_user(userQuery)

                if oAuthProviderQuery.preset_auth_type == "Discord":
                    discord_processLogin(userDataDict, userQuery)
                elif oAuthProviderQuery.preset_auth_type == "Reddit":
                    reddit_processLogin(userDataDict, userQuery)
                elif oAuthProviderQuery.preset_auth_type == "Facebook":
                    facebook_processLogin(oAuthProviderQuery.api_base_url, userDataDict, userQuery)

                if userQuery.email is None or userQuery.email == 'None':
                    flash("Please Add an Email Address to your User Profile", "error")
                    return redirect(url_for('settings.user_page'))
                else:
                    return redirect(url_for('root.main_page'))

        # If No Match, Determine if a User Needs to be created
        else:
            existingEmailQuery = None
            hasEmail = False

            if oAuthProviderQuery.email_value in userDataDict:
                existingEmailQuery = Sec.User.query.filter_by(email=userDataDict[oAuthProviderQuery.email_value]).first()
                hasEmail = True
            else:
                flash("Please Add an Email Address to your User Profile", "error")

            # No Username Match - Create New User
            if existingEmailQuery is None:
                existingUsernameQuery = Sec.User.query.filter_by(username=userDataDict[oAuthProviderQuery.username_value]).first()
                requestedUsername = userDataDict[oAuthProviderQuery.username_value]
                if existingUsernameQuery is not None:
                    requestedUsername = requestedUsername + str(random.randint(1,9999))
                if hasEmail is True:
                    user_datastore.create_user(email=userDataDict[oAuthProviderQuery.email_value], username=requestedUsername, active=True, confirmed_at=datetime.datetime.now(), authType=1, oAuthID=userDataDict[oAuthProviderQuery.id_value], oAuthProvider=provider)
                else:
                    user_datastore.create_user(email=None, username=requestedUsername, active=True, confirmed_at=datetime.datetime.now(), authType=1, oAuthID=userDataDict[oAuthProviderQuery.id_value], oAuthProvider=provider)
                db.session.commit()
                user = Sec.User.query.filter_by(username=requestedUsername).first()
                user_datastore.add_role_to_user(user, 'User')
                user.uuid = str(uuid.uuid4())
                user.xmppToken = str(os.urandom(32).hex())

                if oAuthProviderQuery.preset_auth_type == "Discord":
                    discord_processLogin(userDataDict, user)
                elif oAuthProviderQuery.preset_auth_type == "Reddit":
                    reddit_processLogin(userDataDict, user)
                elif oAuthProviderQuery.preset_auth_type == "Facebook":
                    facebook_processLogin(oAuthProviderQuery.api_base_url, userDataDict, user)

                newToken = None
                if 'refresh_token' in token:
                    newToken = Sec.OAuth2Token(provider, token['token_type'], token['access_token'], token['refresh_token'], token['expires_at'], user.id)
                else:
                    newToken = Sec.OAuth2Token(provider, token['token_type'], token['access_token'], None, token['expires_at'], user.id)
                db.session.add(newToken)
                db.session.commit()
                login_user(user)

                runWebhook("ZZZ", 20, user=user.username)
                newLog(1, "A New User has Registered - Username:" + str(user.username))
                if hasEmail is True:
                    return redirect(url_for('root.main_page'))
                else:
                    return redirect(url_for('settings.user_page'))
            else:
                if existingEmailQuery.authType == 0:
                    return render_template(checkOverride('oAuthConvert.html'), provider=oAuthProviderQuery, oAuthData=userDataDict, existingUser=existingEmailQuery)
                else:
                    flash("An existing OAuth User exists under this email address with another provider", "error")
                    return redirect('/')

@oauth_bp.route('/convert/<provider>',  methods=['POST'])
def oAuthConvert(provider):
    oAuthID = request.form['oAuthID']
    oAuthUserName = request.form['oAuthUsername']
    password = request.form['password']
    existingUserID = request.form['existingUserID']

    userQuery = Sec.User.query.filter_by(id=int(existingUserID), username=oAuthUserName, authType=0).first()
    if userQuery is not None:
        passwordMatch = verify_password(password, userQuery.password)
        if passwordMatch is True:
            userQuery.authType = 1
            userQuery.oAuthProvider = provider
            userQuery.oAuthID = oAuthID
            userQuery.password = None
            db.session.commit()
            flash("Conversion Successful.  Please log in again with your Provider","success")
            return redirect('/login')
        else:
            flash("Invalid Password or Information.  Please try again.", "error")
            return redirect('/login')
    flash("Invalid User!","error")
    return redirect('/login')
