import datetime

from flask import redirect, url_for, Blueprint, flash, abort
from flask_security.utils import login_user
from classes import settings
from classes import Sec
from classes.shared import oauth, db

import json

from app import user_datastore
from functions.oauth import fetch_token

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
        token = oAuthClient.authorize_access_token()

        userData = oAuthClient.get(oAuthProviderQuery.profile_endpoint)
        userDataDict = userData.json()

        userQuery = Sec.User.query.filter_by(username=userDataDict[oAuthProviderQuery.username_value]).first()
        if userQuery != None:
            if userQuery.authType == 1 and userQuery.oAuthProvider == provider:
                existingTokenQuery = Sec.OAuth2Token.query.filter_by(user=userQuery.id).all()
                for existingToken in existingTokenQuery:
                    db.session.delete(existingToken)
                db.session.commit()
                newToken = Sec.OAuth2Token(provider, token.token_type, token.access_token, token.refresh_token, token.expires_at, userQuery.id)
                db.session.add(newToken)
                db.session.commit()
                login_user(userQuery)
                return(redirect(url_for('root.main_page')))
            else:
                flash("A username already exists with that name and is not configured for the oAuth provider or oAuth login","error")
                return(redirect('/login'))
        else:
            user_datastore.create_user(email=userDataDict[oAuthProviderQuery.email_value], username=userDataDict[oAuthProviderQuery.username_value], active=True, confirmed_at=datetime.datetime.now(), authType=1, oAuthProvider=provider)
            db.session.commit()
            user = Sec.User.query.filter_by(username=userDataDict[oAuthProviderQuery.username_value]).first()
            user_datastore.add_role_to_user(user, 'User')
            newToken = Sec.OAuth2Token(provider, token.token_type, token.access_token, token.refresh_token, token.expires_at, userQuery.id)
            db.session.add(newToken)
            db.session.commit()
            login_user(user)

            redirect(url_for('root.main_page'))

