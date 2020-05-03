from flask import redirect, url_for, Blueprint, abort, jsonify
from classes import settings
from classes.shared import oauth

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
        return(jsonify(userData))

