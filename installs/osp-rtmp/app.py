# -*- coding: UTF-8 -*-
from gevent import monkey
monkey.patch_all(thread=True)

# Import Standary Python Libraries

import sys
import logging

# Import 3rd Party Libraries
from flask import Flask, redirect, request, abort, flash
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

# Import Paths
cwp = sys.path[0]
sys.path.append(cwp)

#----------------------------------------------------------------------------#
# Configuration Imports
#----------------------------------------------------------------------------#
try:
    from conf import config

except:
    from dotenv import load_dotenv

    class configObj:
        pass

    load_dotenv()
    config = configObj()

#----------------------------------------------------------------------------#
# Global Vars Imports
#----------------------------------------------------------------------------#
from globals import globalvars

#----------------------------------------------------------------------------#
# App Configuration Setup
#----------------------------------------------------------------------------#
coreNginxRTMPAddress = "127.0.0.1"

globalvars.apiLocation = config.ospCoreAPI

app = Flask(__name__)

# Flask App Environment Setup
app.debug = config.debugMode
app.wsgi_app = ProxyFix(app.wsgi_app)
app.jinja_env.cache = {}
app.config['WEB_ROOT'] = globalvars.videoRoot

app.config['SESSION_COOKIE_SAMESITE'] = "Lax"
app.config['SESSION_COOKIE_NAME'] = 'ospSession'
app.config['SECRET_KEY'] = config.secretKey

logger = logging.getLogger('gunicorn.error').handlers

#----------------------------------------------------------------------------#
# Begin App Initialization
#----------------------------------------------------------------------------#

# Initialize Flask-CORS Config
cors = CORS(app, resources={r"/apiv1/*": {"origins": "*"}})

#----------------------------------------------------------------------------#
# Blueprint Filter Imports
#----------------------------------------------------------------------------#
from blueprints.rtmp import rtmp_bp
from blueprints.root import root_bp
from blueprints.api import api_v1

# Register all Blueprints
app.register_blueprint(rtmp_bp)
app.register_blueprint(root_bp)
app.register_blueprint(api_v1)

#----------------------------------------------------------------------------#
# Finalize App Init
#----------------------------------------------------------------------------#
if __name__ == '__main__':
    app.run(Debug=config.debugMode)
