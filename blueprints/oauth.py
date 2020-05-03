from flask import redirect, url_for, Blueprint, abort
from classes import settings
from classes import Sec
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
        userDataDict = userData.json()

        userQuery = Sec.User.query.filter_by(username=userDataDict[oAuthProviderQuery.username_value]).first()
        if userQuery != None:
            if userQuery.type == 1 and userQuery.oAuthProvider == provider:
                return("Existing User - Success")
            else:
                return("Existing User - Failure: Not for Provider or Not oAuth Login")
        else:
            return("No User - Create User Here")

