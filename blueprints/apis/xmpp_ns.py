from flask_restplus import Api, Resource, reqparse, Namespace

from classes import settings
from classes import Sec
from classes.shared import db

api = Namespace('XMPP', description='XMPP Chat Related Queries and Functions')

xmppAuthParserPost = reqparse.RequestParser()
xmppAuthParserPost.add_argument('jid', type=str)
xmppAuthParserPost.add_argument('token', type=str)

xmppIsUserParserPost = reqparse.RequestParser()
xmppIsUserParserPost.add_argument('jid', type=str)

@api.route('/xmpp/auth')
@api.doc(params={'jid': 'JID of user', 'token': 'Jabber Token'})
class api_1_xmppAuth(Resource):
    @api.expect(xmppAuthParserPost)
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def post(self):
        """
        Verify Chat Authentication
        """
        args = xmppAuthParserPost.parse_args()
        if 'jid' in args:
            jid = args['jid']
            if 'token' in args:
                token = args['token']
                sysSettings = settings.settings.query.first()
                if sysSettings is not None:
                    username = jid.replace("@" + sysSettings.siteAddress,"")
                    userQuery = Sec.User.query.filter_by(uuid=username, active=True).first()
                    if userQuery != None:
                        if userQuery.xmppToken == token:
                            return {'results': {'message': 'Successful Authentication', 'code': 200}}, 200
        return {'results': {'message': 'Request Error', 'code':400}}, 400


@api.route('/xmpp/isuser')
@api.doc(params={'jid': 'JID of user'})
class api_1_xmppisuser(Resource):
    @api.expect(xmppIsUserParserPost)
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def post(self):
        """
        Verify if User
        """
        args = xmppIsUserParserPost.parse_args()
        if 'jid' in args:
            jid = args['jid']
            sysSettings = settings.settings.query.first()
            if sysSettings is not None:
                username = jid.replace("@" + sysSettings.siteAddress,"")
                userQuery = Sec.User.query.filter_by(uuid=username).first()
                if userQuery != None:
                    return {'results': {'message': 'Successful Authentication', 'code': 200}}, 200
        return {'results': {'message': 'Request Error', 'code':400}}, 400