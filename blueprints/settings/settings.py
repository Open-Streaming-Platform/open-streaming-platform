import os
import datetime
import json
import uuid
import socket

from flask import (
    request,
    flash,
    render_template,
    redirect,
    url_for,
    Blueprint,
    current_app,
    session,
)
from flask_security import (
    current_user,
    login_required,
    roles_required,
)
from flask_security.utils import hash_password

from classes.shared import db, email
from classes import settings
from classes import Sec
from classes import apikey
from classes.shared import cache

from functions import system
from functions import themes
from functions import cachedDbCalls

from globals import globalvars

from app import user_datastore

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")

from .user import user_settings_bp
from .admin import admin_settings_bp
from .channels import channel_settings_bp

settings_bp.register_blueprint(user_settings_bp)
settings_bp.register_blueprint(admin_settings_bp)
settings_bp.register_blueprint(channel_settings_bp)

@settings_bp.route("/api", methods=["GET"])
@login_required
@roles_required("Streamer")
def settings_apikeys_page():
    apiKeyQuery = apikey.apikey.query.filter_by(userID=current_user.id).all()
    return render_template(themes.checkOverride("apikeys.html"), apikeys=apiKeyQuery)


@settings_bp.route("/api/<string:action>", methods=["POST"])
@login_required
@roles_required("Streamer")
def settings_apikeys_post_page(action):
    if action == "new":
        validKeyTypes = [1, 2]
        validRequest = False
        if "keyType" in request.form:
            requestedKeyType = int(request.form["keyType"])
            if requestedKeyType in validKeyTypes:
                if requestedKeyType == 2:
                    if current_user.has_role("Admin"):
                        validRequest = True
                else:
                    validRequest = True
        if validRequest is True:
            newapi = apikey.apikey(
                current_user.id,
                requestedKeyType,
                request.form["keyName"],
                request.form["expiration"],
            )
            db.session.add(newapi)
            flash("New API Key Added", "success")
        else:
            flash("Invalid Key Type", "error")
        db.session.commit()

    elif action == "delete":
        apiQuery = apikey.apikey.query.filter_by(key=request.form["key"]).first()
        if apiQuery.userID == current_user.id:
            db.session.delete(apiQuery)
            db.session.commit()
            flash("API Key Deleted", "success")
        else:
            flash("Invalid API Key", "error")
    return redirect(url_for(".settings_apikeys_page"))


@settings_bp.route("/initialSetup", methods=["POST"])
def initialSetup():
    firstRunCheck = system.check_existing_settings()

    if firstRunCheck is False:
        cache.delete_memoized(cachedDbCalls.getSystemSettings)
        sysSettings = settings.settings.query.all()

        for setting in sysSettings:
            db.session.delete(setting)
        db.session.commit()

        username = request.form["username"]
        emailAddress = request.form["email"]
        password1 = request.form["password1"]
        password2 = request.form["password2"]
        serverName = request.form["serverName"]
        serverProtocol = str(request.form["siteProtocol"])
        serverAddress = str(request.form["serverAddress"])

        recordSelect = False
        uploadSelect = False
        adaptiveStreaming = False
        showEmptyTables = False
        allowComments = False

        if "recordSelect" in request.form:
            recordSelect = True

        if "uploadSelect" in request.form:
            uploadSelect = True

        if "adaptiveStreaming" in request.form:
            adaptiveStreaming = True

        if "showEmptyTables" in request.form:
            showEmptyTables = True

        if "allowComments" in request.form:
            allowComments = True

        # Whereas this code had worked before, it is now causing errors on post
        # validAddress = system.formatSiteAddress(serverAddress)
        # try:
        #    externalIP = socket.gethostbyname(validAddress)
        # except socket.gaierror:
        #    flash("Invalid Server Address/IP", "error")
        #    return redirect(url_for("settings.initialSetup"))

        if password1 == password2:

            passwordhash = hash_password(password1)

            user_datastore.create_user(
                email=emailAddress, username=username, password=passwordhash
            )
            db.session.commit()
            user = Sec.User.query.filter_by(username=username).first()
            user.uuid = str(uuid.uuid4())
            user.authType = 0
            user.confirmed_at = datetime.datetime.utcnow()
            user.xmppToken = str(os.urandom(32).hex())

            user_datastore.find_or_create_role(
                name="Admin", description="Administrator"
            )
            user_datastore.find_or_create_role(name="User", description="User")
            user_datastore.find_or_create_role(name="Streamer", description="Streamer")
            user_datastore.find_or_create_role(name="Recorder", description="Recorder")
            user_datastore.find_or_create_role(name="Uploader", description="Uploader")

            user_datastore.add_role_to_user(user, "Admin")
            user_datastore.add_role_to_user(user, "Streamer")
            user_datastore.add_role_to_user(user, "Recorder")
            user_datastore.add_role_to_user(user, "Uploader")
            user_datastore.add_role_to_user(user, "User")

            serverSettings = settings.settings(
                serverName,
                serverProtocol,
                serverAddress,
                recordSelect,
                uploadSelect,
                adaptiveStreaming,
                showEmptyTables,
                allowComments,
                globalvars.version,
            )
            db.session.add(serverSettings)
            db.session.commit()

            sysSettings = cachedDbCalls.getSystemSettings()

            if settings is not None:
                current_app.config.update(
                    SERVER_NAME=None,
                    SECURITY_EMAIL_SUBJECT_PASSWORD_RESET=sysSettings.siteName
                    + " - Password Reset Request",
                    SECURITY_EMAIL_SUBJECT_REGISTER=sysSettings.siteName
                    + " - Welcome!",
                    SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE=sysSettings.siteName
                    + " - Password Reset Notification",
                    SECURITY_EMAIL_SUBJECT_CONFIRM=sysSettings.siteName
                    + " - Email Confirmation Request",
                    SECURITY_FORGOT_PASSWORD_TEMPLATE="security/forgot_password.html",
                    SECURITY_LOGIN_USER_TEMPLATE="security/login_user.html",
                    SECURITY_REGISTER_USER_TEMPLATE="security/register_user.html",
                    SECURITY_RESET_PASSWORD_TEMPLATE="security/reset_password.html",
                    SECURITY_SEND_CONFIRMATION_TEMPLATE="security/send_confirmation.html",
                )

                email.init_app(current_app)
                email.app = current_app

                # Import Theme Data into Theme Dictionary
                with open(
                    "templates/themes/" + sysSettings.systemTheme + "/theme.json"
                ) as f:
                    globalvars.themeData = json.load(f)

        else:
            flash("Passwords do not match")
            return redirect(url_for("root.main_page"))

    return redirect(url_for("root.main_page"))
