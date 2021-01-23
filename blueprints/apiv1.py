import sys
from os import path, remove
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from flask import Blueprint, request, url_for
from flask_restplus import Api, Resource, reqparse

import shutil
import uuid
import datetime
import socket

from classes import Sec
from classes import Channel
from classes import Stream
from classes import RecordedVideo
from classes import topics
from classes import upvotes
from classes import apikey
from classes import views
from classes import settings
from classes.shared import db

from functions import rtmpFunc
from functions import system

from globals import globalvars

from .apis.server_ns import api as serverNS
from .apis.channel_ns import api as channelNS
from .apis.stream_ns import api as streamNS
from .apis.video_ns import api as videoNS
from .apis.clip_ns import api as clipNS
from .apis.topic_ns import api as topicNS
from .apis.user_ns import api as userNS
from .apis.xmpp_ns import api as xmppNS
from .apis.rtmp_ns import api as rtmpNS


def isValidAdminKey(apikey):
    validKey = False
    apiKeyQuery = apikey.apikey.query.filter_by(type=2, key=apikey).first()
    if apiKeyQuery is not None:
        if apiKeyQuery.isValid() is True:
            userID = apiKeyQuery.userID
            userQuery = Sec.User.query.filter_by(id=userID).first()
            if userQuery is not None:
                if userQuery.has_role("Admin"):
                    validKey = True
    return validKey


class fixedAPI(Api):
    # Monkeyfixed API IAW https://github.com/noirbizarre/flask-restplus/issues/223
    @property
    def specs_url(self):
        '''
        The Swagger specifications absolute url (ie. `swagger.json`)

        :rtype: str
        '''
        return url_for(self.endpoint('specs'), _external=False)


authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}

api_v1 = Blueprint('api', __name__, url_prefix='/apiv1')
api = fixedAPI(api_v1, version='1.0', title='OSP API', description='OSP API for Users, Streamers, and Admins', default='Primary', default_label='OSP Primary Endpoints', authorizations=authorizations)

api.add_namespace(serverNS)
api.add_namespace(channelNS)
api.add_namespace(streamNS)
api.add_namespace(videoNS)
api.add_namespace(clipNS)
api.add_namespace(topicNS)
api.add_namespace(userNS)
api.add_namespace(xmppNS)
api.add_namespace(rtmpNS)
