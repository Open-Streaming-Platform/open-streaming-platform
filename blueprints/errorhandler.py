from flask import Blueprint, request, render_template

from classes import settings

from functions import themes
from functions import system
from functions import cachedDbCalls

errorhandler_bp = Blueprint('errors', __name__)

@errorhandler_bp.app_errorhandler(404)
def page_not_found(e):
    sysSettings = cachedDbCalls.getSystemSettings()
    system.newLog(0, "404 Error - " + str(request.url))
    return render_template(themes.checkOverride('404.html'), sysSetting=sysSettings, previous=request.referrer), 404

@errorhandler_bp.app_errorhandler(500)
def page_not_found(e):
    sysSettings = cachedDbCalls.getSystemSettings()
    system.newLog(0,"500 Error - " + str(request.url))
    return render_template(themes.checkOverride('500.html'), sysSetting=sysSettings, previous=request.referrer, error=e), 500