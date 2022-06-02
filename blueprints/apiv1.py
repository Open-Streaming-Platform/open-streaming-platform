import sys
from os import path, remove
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from flask import Blueprint, url_for
from flask_restx import Api, Resource, reqparse


from .apis.server_ns import api as serverNS
from .apis.channel_ns import api as channelNS
from .apis.stream_ns import api as streamNS
from .apis.video_ns import api as videoNS
from .apis.clip_ns import api as clipNS
from .apis.topic_ns import api as topicNS
from .apis.user_ns import api as userNS
from .apis.xmpp_ns import api as xmppNS
from .apis.rtmp_ns import api as rtmpNS


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
