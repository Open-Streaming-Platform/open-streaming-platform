from flask import redirect, url_for, Blueprint, abort
from classes import settings

#from globals.globalvars import oAuthProviderObjects
from app import oAuthProviderList

oauth_bp = Blueprint('oauth', __name__, url_prefix='/oauth')

@oauth_bp.route('/login/<provider>')
def oAuthLogin(provider):
    sysSettings = settings.settings.query.first()
    if sysSettings is not None:
        if provider in oAuthProviderList:
            redirect_url = sysSettings.siteProtocol + sysSettings.siteAddress + '/oauth/authorize/' + provider
            return oAuthProviderList[provider].authorize_redirect(redirect_url)
        else:
            abort(500)
    else:
        redirect(url_for('root.main_page'))

@oauth_bp.route('/authorize/<provider>')
def oAuthAuthorize(provider):
    if provider in oAuthProviderList:
        oAuthProviderQuery = settings.oAuthProvider.query.filter_by(name=provider).first()
        if oAuthProviderQuery is not None:
            token = oAuthProviderList[provider].authorize_access_token()
            userData = oAuthProviderList[provider].get(oAuthProviderQuery.profile_endpoint)
            return(str(userData))

