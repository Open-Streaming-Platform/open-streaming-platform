# -*- coding: UTF-8 -*-
from gevent import monkey
monkey.patch_all(thread=True)

# Import Standary Python Libraries
import socket
import os
import subprocess
import time
import sys
import hashlib
import logging
import datetime
import json
import uuid
import time
import random

# Import 3rd Party Libraries
from flask import Flask, redirect, request, abort, flash, current_app, session
from flask_session import Session
from flask_security import Security, SQLAlchemyUserDatastore, login_required, current_user, roles_required, uia_email_mapper
from flask_security.signals import user_registered
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class
from flask_migrate import Migrate
from flaskext.markdown import Markdown
from flask_debugtoolbar import DebugToolbarExtension
from flask_cors import CORS
from flask_babelex import Babel
from werkzeug.middleware.proxy_fix import ProxyFix

import redis
from apscheduler.schedulers.background import BackgroundScheduler

# Import Paths
cwp = sys.path[0]
sys.path.append(cwp)
sys.path.append('./classes')

#----------------------------------------------------------------------------#
# Configuration Imports
#----------------------------------------------------------------------------#
from conf import config

#----------------------------------------------------------------------------#
# Global Vars Imports
#----------------------------------------------------------------------------#
from globals import globalvars

#----------------------------------------------------------------------------#
# App Configuration Setup
#----------------------------------------------------------------------------#
# Generate a Random UUID for Interprocess Handling
processUUID = str(uuid.uuid4())
globalvars.processUUID = processUUID

####### Sentry.IO Metrics and Error Logging (Disabled by Default) #######
if hasattr(config, 'sentryIO_Enabled') and hasattr(config, 'sentryIO_DSN'):
    if config.sentryIO_Enabled:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentryEnv = "Not Specified"
        if hasattr(config, 'sentryIO_Environment'):
            sentryEnv = config.sentryIO_Environment

        sentry_sdk.init(
            dsn=config.sentryIO_DSN,
            integrations=[FlaskIntegration(), SqlalchemyIntegration()],

            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            # We recommend adjusting this value in production.
            traces_sample_rate=1.0,
            release=globalvars.version,
            environment=sentryEnv,
            server_name=globalvars.processUUID
        )

coreNginxRTMPAddress = "127.0.0.1"

app = Flask(__name__)

# Flask App Environment Setup
app.debug = config.debugMode
app.wsgi_app = ProxyFix(app.wsgi_app)
app.jinja_env.cache = {}
app.config['WEB_ROOT'] = globalvars.videoRoot
app.config['SQLALCHEMY_DATABASE_URI'] = config.dbLocation
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
if config.dbLocation[:6] != "sqlite":
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = -1
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 300
    app.config['SQLALCHEMY_POOL_TIMEOUT'] = 600
    app.config['MYSQL_DATABASE_CHARSET'] = "utf8"
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'encoding': 'utf8', 'pool_use_lifo': 'False', 'pool_size': 10, "pool_pre_ping": True}
else:
    pass
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_COOKIE_SAMESITE'] = "Lax"
app.config['SESSION_COOKIE_NAME'] = 'ospSession'
app.config['SECRET_KEY'] = config.secretKey
app.config['SECURITY_PASSWORD_HASH'] = "pbkdf2_sha512"
app.config['SECURITY_PASSWORD_SALT'] = config.passwordSalt
app.config['SECURITY_REGISTERABLE'] = config.allowRegistration
app.config['SECURITY_RECOVERABLE'] = True
app.config['SECURITY_CONFIRMABLE'] = config.requireEmailRegistration
app.config['SECURITY_SEND_REGISTER_EMAIL'] = config.requireEmailRegistration
app.config['SECURITY_CHANGABLE'] = True
app.config['SECURITY_TRACKABLE'] = True
app.config['SECURITY_TWO_FACTOR_ENABLED_METHODS'] = ['authenticator']
app.config['SECURITY_TWO_FACTOR'] = True
app.config['SECURITY_TWO_FACTOR_ALWAYS_VALIDATE']=False
app.config['SECURITY_TWO_FACTOR_LOGIN_VALIDITY']='1 week'
app.config['SECURITY_TOTP_SECRETS'] = {"1": config.secretKey}
app.config['SECURITY_FLASH_MESSAGES'] = True
app.config['UPLOADED_PHOTOS_DEST'] = app.config['WEB_ROOT'] + 'images'
app.config['UPLOADED_STICKERS_DEST'] = app.config['WEB_ROOT'] + 'images'
app.config['UPLOADED_DEFAULT_DEST'] = app.config['WEB_ROOT'] + 'images'
app.config['SECURITY_POST_LOGIN_VIEW'] = '/'
app.config['SECURITY_POST_LOGOUT_VIEW'] = '/'
app.config['SECURITY_MSG_EMAIL_ALREADY_ASSOCIATED'] = ("Username or Email Already Associated with an Account", "error")
app.config['SECURITY_MSG_INVALID_PASSWORD'] = ("Invalid Username or Password", "error")
app.config['SECURITY_MSG_INVALID_EMAIL_ADDRESS'] = ("Invalid Username or Password","error")
app.config['SECURITY_MSG_USER_DOES_NOT_EXIST'] = ("Invalid Username or Password","error")
app.config['SECURITY_MSG_DISABLED_ACCOUNT'] = ("Account Disabled","error")
app.config['VIDEO_UPLOAD_TEMPFOLDER'] = app.config['WEB_ROOT'] + 'videos/temp'
app.config["VIDEO_UPLOAD_EXTENSIONS"] = ["PNG", "MP4"]

# Initialize Recaptcha
if hasattr(config, 'RECAPTCHA_ENABLED'):
    if config.RECAPTCHA_ENABLED is True:
        globalvars.recaptchaEnabled = True
        try:
            app.config['RECAPTCHA_PUBLIC_KEY'] = config.RECAPTCHA_SITE_KEY
            app.config['RECAPTCHA_PRIVATE_KEY'] = config.RECAPTCHA_SECRET_KEY
        except:
            logging.warning("Recaptcha Enabled, but missing Site Key or Secret Key in config.py.  Disabling ReCaptcha")
            globalvars.recaptchaEnabled = False

#----------------------------------------------------------------------------#
# Modal Imports
#----------------------------------------------------------------------------#

from classes import Stream
from classes import Channel
from classes import dbVersion
from classes import RecordedVideo
from classes import topics
from classes import settings
from classes import banList
from classes import Sec
from classes import upvotes
from classes import apikey
from classes import views
from classes import comments
from classes import invites
from classes import webhook
from classes import logs
from classes import subscriptions
from classes import notifications
from classes import stickers

#----------------------------------------------------------------------------#
# Function Imports
#----------------------------------------------------------------------------#
from functions import database
from functions import system
from functions import securityFunc
from functions import votes
from functions import webhookFunc
from functions.ejabberdctl import ejabberdctl
from functions import cachedDbCalls
#----------------------------------------------------------------------------#
# Begin App Initialization
#----------------------------------------------------------------------------#
logger = logging.getLogger('gunicorn.error').handlers

# Initialize Flask-BabelEx
babel = Babel(app)

# Initialize RedisURL
RedisURL = None
if config.redisPassword == '' or config.redisPassword is None:
    RedisURL = "redis://" + config.redisHost + ":" + str(config.redisPort)
else:
    RedisURL = "redis://:" + config.redisPassword + "@" + config.redisHost + ":" + str(config.redisPort)

#Initialize Flask-Limiter
app.config["RATELIMIT_STORAGE_URL"] = RedisURL
from classes.shared import limiter
limiter.init_app(app)

# Initialize Redis for Flask-Session
if config.redisPassword == '' or config.redisPassword is None:
    r = redis.Redis(host=config.redisHost, port=config.redisPort)
    app.config["SESSION_REDIS"] = r
else:
    r = redis.Redis(host=config.redisHost, port=config.redisPort, password=config.redisPassword)
    app.config["SESSION_REDIS"] = r
r.flushdb()

# Initialize Flask-SocketIO
from classes.shared import socketio
if config.redisPassword == '' or config.redisPassword is None:
    socketio.init_app(app, logger=False, engineio_logger=False, message_queue="redis://" + config.redisHost + ":" + str(config.redisPort), ping_interval=20, ping_timeout=40, cookie=None, cors_allowed_origins=[])
else:
    socketio.init_app(app, logger=False, engineio_logger=False, message_queue="redis://:" + config.redisPassword + "@" + config.redisHost + ":" + str(config.redisPort), ping_interval=20, ping_timeout=40, cookie=None, cors_allowed_origins=[])

# Initialize Flask-Celery
from classes.shared import celery
celery.conf.broker_url = RedisURL
celery.conf.result_backend = RedisURL
celery.conf.update(app.config)

class ContextTask(celery.Task):
    """Make celery tasks work with Flask app context"""
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)
celery.Task = ContextTask

# Begin Database Initialization
from classes.shared import db
db.init_app(app)
db.app = app
migrateObj = Migrate(app, db)

# Initialize Flask-Session
Session(app)

# Initialize Flask-CORS Config
cors = CORS(app, resources={r"/apiv1/*": {"origins": "*"}})

# Initialize Flask-Caching
logging.info({"level": "info", "message": "Performing Flask Caching Initialization"})

from classes.shared import cache
redisCacheOptions = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_KEY_PREFIX': 'OSP_FC',
    'CACHE_REDIS_HOST': config.redisHost,
    'CACHE_REDIS_PORT': config.redisPort,
}
if config.redisPassword != '' and config.redisPassword is not None:
    redisCacheOptions['CACHE_REDIS_PASSWORD'] = config.redisPassword
cache.init_app(app, config=redisCacheOptions)

# Initialize Debug Toolbar
toolbar = DebugToolbarExtension(app)

# Initialize Flask-Security
try:
    sysSettings = cachedDbCalls.getSystemSettings()
    app.config['SECURITY_TOTP_ISSUER'] = sysSettings.siteName
except:
    app.config['SECURITY_TOTP_ISSUER'] = "OSP"
    app.config['SECURITY_USER_IDENTITY_ATTRIBUTES'] = [
        {"email": {"mapper": uia_email_mapper, "case_insensitive": True}}
    ]

user_datastore = SQLAlchemyUserDatastore(db, Sec.User, Sec.Role)
security = Security(app, user_datastore, register_form=Sec.ExtendedRegisterForm, confirm_register_form=Sec.ExtendedConfirmRegisterForm, login_form=Sec.OSPLoginForm)

# Initialize Flask-Uploads
photos = UploadSet('photos', IMAGES)
stickerUploads = UploadSet('stickers', IMAGES)
configure_uploads(app, (photos, stickerUploads))
patch_request_class(app)

# Initialize Flask-Markdown
md = Markdown(app, extensions=['tables'])

# Initialize ejabberdctl
ejabberd = None

if hasattr(config,'ejabberdServer'):
    globalvars.ejabberdServer = config.ejabberdServer
if hasattr(config,'ejabberdServerHttpBindFQDN'):
    globalvars.ejabberdServerHttpBindFQDN = config.ejabberdServerHttpBindFQDN

try:
    ejabberd = ejabberdctl(config.ejabberdHost, config.ejabberdAdmin, config.ejabberdPass, server=globalvars.ejabberdServer)
    logging.info(ejabberd.status())
except Exception as e:
    logging.error("ejabberdctl failed to load: " + str(e))

# Loop Check if OSP DB Init is Currently Being Handled by and Process
OSP_DB_INIT_HANDLER = None
while OSP_DB_INIT_HANDLER != globalvars.processUUID:
    OSP_DB_INIT_HANDLER = r.get('OSP_DB_INIT_HANDLER')
    if OSP_DB_INIT_HANDLER != None:
        OSP_DB_INIT_HANDLER = OSP_DB_INIT_HANDLER.decode('utf-8')
    else:
        r.set('OSP_DB_INIT_HANDLER', globalvars.processUUID)
        time.sleep(random.random())

# Once Attempt Database Load and Validation
try:
    database.init(app, user_datastore)
except:
    logging.warning("DB Load Fail due to Upgrade or Issues")
# Clear Process from OSP DB Init
r.delete('OSP_DB_INIT_HANDLER')

# Perform System Fixes
try:
    system.systemFixes(app)
except:
    logging.warning({"level": "error", "message": "Unable to perform System Fixes.  May be first run or DB Issue."})

if r.get('OSP_XMPP_INIT_HANDLER') is None:
    # Perform XMPP Sanity Check
    r.set('OSP_XMPP_INIT_HANDLER', globalvars.processUUID, ex=60)
    logging.info({"level": "info", "message": "Performing XMPP Sanity Checks"})
    from functions import xmpp
    try:
        results = xmpp.sanityCheck()
    except Exception as e:
        logging.error({"level": "error", "message": "XMPP Sanity Check Failed - " + str(e)})
        r.delete('OSP_XMPP_INIT_HANDLER')
else:
    logging.info({"level": "info", "message": "Process Skipping XMPP Sanity Check - Already in Progress or Recently Run"})

# Checking OSP-Edge Redirection Conf File
try:
    system.checkOSPEdgeConf()
except:
    logging.warning({"level": "error", "message": "Unable to initialize OSP Edge Conf.  May be first run or DB Issue."})
logging.info({"level": "info", "message": "Initializing OAuth Info"})
# Initialize oAuth
from classes.shared import oauth
from functions.oauth import fetch_token
oauth.init_app(app, fetch_token=fetch_token)

try:
# Register oAuth Providers
    for provider in settings.oAuthProvider.query.all():
        try:
            oauth.register(
                name=provider.name,
                client_id=provider.client_id,
                client_secret=provider.client_secret,
                access_token_url=provider.access_token_url,
                access_token_params=provider.access_token_params if (provider.access_token_params != '' and provider.access_token_params is not None) else None,
                authorize_url=provider.authorize_url,
                authorize_params=provider.authorize_params if (provider.authorize_params != '' and provider.authorize_params is not None) else None,
                api_base_url=provider.api_base_url,
                client_kwargs=json.loads(provider.client_kwargs) if (provider.client_kwargs != '' and provider.client_kwargs is not None) else None,
            )

        except Exception as e:
            logging.error("Failed Loading oAuth Provider-" + provider.name + ":" + str(e))
except:
    logging.error("Failed Loading oAuth Providers")

logging.info({"level": "info", "message": "Initializing Flask-Mail"})
# Initialize Flask-Mail
from classes.shared import email

email.init_app(app)
email.app = app

logging.info({"level": "info", "message": "Importing Topic Data into Global Cache"})
# Initialize the Topic Cache
topicQuery = topics.topics.query.all()
for topic in topicQuery:
    globalvars.topicCache[topic.id] = topic.name

# Initialize First Theme Overrides
try:
    system.initializeThemes()
except:
    logging.warning({"level": "error", "message": "Unable to Set Override Themes"})

logging.info({"level": "info", "message": "Initializing SocketIO Handlers"})
#----------------------------------------------------------------------------#
# SocketIO Handler Import
#----------------------------------------------------------------------------#
from functions.socketio import connections
from functions.socketio import video
from functions.socketio import stream
from functions.socketio import vote
from functions.socketio import invites
from functions.socketio import webhooks
from functions.socketio import edge
from functions.socketio import subscription
from functions.socketio import thumbnail
from functions.socketio import syst
from functions.socketio import xmpp
from functions.socketio import restream
from functions.socketio import rtmp
from functions.socketio import pictures

logging.info({"level": "info", "message": "Initializing Flask Blueprints"})
#----------------------------------------------------------------------------#
# Blueprint Filter Imports
#----------------------------------------------------------------------------#
from blueprints.errorhandler import errorhandler_bp
from blueprints.apiv1 import api_v1
from blueprints.root import root_bp
from blueprints.streamers import streamers_bp
from blueprints.profile import profile_bp
from blueprints.channels import channels_bp
from blueprints.topics import topics_bp
from blueprints.play import play_bp
from blueprints.liveview import liveview_bp
from blueprints.clip import clip_bp
from blueprints.upload import upload_bp
from blueprints.settings import settings_bp
from blueprints.oauth import oauth_bp

# Register all Blueprints
app.register_blueprint(errorhandler_bp)
app.register_blueprint(api_v1)
app.register_blueprint(root_bp)
app.register_blueprint(channels_bp)
app.register_blueprint(play_bp)
app.register_blueprint(clip_bp)
app.register_blueprint(streamers_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(topics_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(liveview_bp)
app.register_blueprint(oauth_bp)

logging.info({"level": "info", "message": "Initializing Template Filters"})
#----------------------------------------------------------------------------#
# Template Filter Imports
#----------------------------------------------------------------------------#
from functions import templateFilters

# Initialize Jinja2 Template Filters
templateFilters.init(app)

logging.info({"level": "info", "message": "Setting Jinja2 Global Env Functions"})
#----------------------------------------------------------------------------#
# Jinja 2 Gloabl Environment Functions
#----------------------------------------------------------------------------#
app.jinja_env.globals.update(check_isValidChannelViewer=securityFunc.check_isValidChannelViewer)
app.jinja_env.globals.update(check_isCommentUpvoted=votes.check_isCommentUpvoted)

logging.info({"level": "info", "message": "Setting Flask Context Processors"})
#----------------------------------------------------------------------------#
# Context Processors
#----------------------------------------------------------------------------#
@app.context_processor
def inject_notifications():
    notificationList = []
    if current_user.is_authenticated:
        userNotificationQuery = notifications.userNotification.query.filter_by(userID=current_user.id).all()
        for entry in userNotificationQuery:
            if entry.read is False:
                notificationList.append(entry)
        notificationList.sort(key=lambda x: x.timestamp, reverse=True)
    return dict(notifications=notificationList)

@app.context_processor
def inject_recaptchaEnabled():
    recaptchaEnabled = globalvars.recaptchaEnabled
    return dict(recaptchaEnabled=recaptchaEnabled)

@app.context_processor
def inject_oAuthProviders():

    SystemOAuthProviders = cachedDbCalls.getOAuthProviders()
    return dict(SystemOAuthProviders=SystemOAuthProviders)

@app.context_processor
def inject_sysSettings():

    sysSettings = cachedDbCalls.getSystemSettings()
    allowRegistration = config.allowRegistration
    return dict(sysSettings=sysSettings, allowRegistration=allowRegistration)

@app.context_processor
def inject_ownedChannels():
    if current_user.is_authenticated:
        if current_user.has_role("Streamer"):
            ownedChannels = Channel.Channel.query.filter_by(owningUser=current_user.id).with_entities(Channel.Channel.id, Channel.Channel.channelLoc, Channel.Channel.channelName).all()

            return dict(ownedChannels=ownedChannels)
        else:
            return dict(ownedChannels=[])
    else:
        return dict(ownedChannels=[])

@app.context_processor
def inject_topics():
    topicQuery = topics.topics.query.with_entities(topics.topics.id, topics.topics.name).all()
    return dict(uploadTopics=topicQuery)

logging.info({"level": "info", "message": "Initializing Flask Signal Handlers"})
#----------------------------------------------------------------------------#
# Flask Signal Handlers.
#----------------------------------------------------------------------------#
@user_registered.connect_via(app)
def user_registered_sighandler(app, user, confirm_token, form_data=None):
    defaultRoleQuery = Sec.Role.query.filter_by(default=True).all()
    for role in defaultRoleQuery:
        user_datastore.add_role_to_user(user, role.name)
    user.authType = 0
    user.xmppToken = str(os.urandom(32).hex())
    user.uuid = str(uuid.uuid4())
    webhookFunc.runWebhook("ZZZ", 20, user=user.username)
    system.newLog(1, "A New User has Registered - Username:" + str(user.username))
    if config.requireEmailRegistration:
        flash("An email has been sent to the email provided. Please check your email and verify your account to activate.")
    db.session.commit()

#----------------------------------------------------------------------------#
# Additional Handlers.
#----------------------------------------------------------------------------#

@app.before_request
def do_before_request():
    # Check all IP Requests for banned IP Addresses
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        requestIP = request.environ['REMOTE_ADDR']
    else:
        requestIP = request.environ['HTTP_X_FORWARDED_FOR']

    if requestIP != "127.0.0.1":
        try:
            banQuery = banList.ipList.query.filter_by(ipAddress=requestIP).first()
            if banQuery != None:
                return str({'error': 'banned', 'reason': banQuery.reason})

            # Apply Guest UUID in Session and Handle Object
            if current_user.is_authenticated is False:
                if 'guestUUID' not in session:
                    session['guestUUID'] = str(uuid.uuid4())
                GuestQuery = Sec.Guest.query.filter_by(UUID=session['guestUUID']).first()
                if GuestQuery is not None:
                    GuestQuery.last_active_at = datetime.datetime.utcnow()
                    GuestQuery.last_active_ip = requestIP
                    db.session.commit()
                else:
                    # Check if a previous access from an IP Address was Used
                    GuestQuery = Sec.Guest.query.filter_by(last_active_ip=requestIP).first()
                    if GuestQuery is not None:
                        GuestQuery.last_active_at = datetime.datetime.utcnow()
                        GuestQuery.UUID = session['guestUUID']
                        db.session.commit()
                    else:
                        NewGuest = Sec.Guest(session['guestUUID'], requestIP)
                        db.session.add(NewGuest)
                        db.session.commit()
        except:
            pass

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

logging.info({"level": "info", "message": "Finalizing App Initialization"})
#----------------------------------------------------------------------------#
# Finalize App Init
#----------------------------------------------------------------------------#
try:
    system.newLog("0", "OSP Started Up Successfully - version: " + str(globalvars.version))
    logging.info({"level": "info", "message": "OSP Core Node Started Successfully-" + str(globalvars.version)})
except:
    pass
if __name__ == '__main__':
    app.jinja_env.auto_reload = False
    app.config['TEMPLATES_AUTO_RELOAD'] = False
    socketio.run(app, Debug=config.debugMode)
