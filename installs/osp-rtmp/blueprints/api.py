import sys
from os import path, remove

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from flask import Blueprint, url_for
from flask_restx import Api, Resource, reqparse

from .apis.server_ns import api as serverNS


class fixedAPI(Api):
    # Monkeyfixed API IAW https://github.com/noirbizarre/flask-restplus/issues/223
    @property
    def specs_url(self):
        """
        The Swagger specifications absolute url (ie. `swagger.json`)

        :rtype: str
        """
        return url_for(self.endpoint("specs"), _external=False)


authorizations = {"apikey": {"type": "apiKey", "in": "header", "name": "X-API-KEY"}}

api_v1 = Blueprint("api", __name__, url_prefix="/api")
api = fixedAPI(
    api_v1,
    version="1.0",
    title="OSP-RTMP API",
    description="OSP-RTMP",
    default="Primary",
    default_label="OSP-RTMP Primary Endpoints",
    authorizations=authorizations,
)

api.add_namespace(serverNS)
