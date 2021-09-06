from flask_restplus import Api, Resource, reqparse, Namespace

from classes import topics
from classes.shared import db

from functions import cachedDbCalls

api = Namespace('topic', description='Topic Related Queries and Functions')

@api.route('/')
class api_1_ListTopics(Resource):
    def get(self):
        """
             Returns a List of All Topics
        """
        topicList = cachedDbCalls.getAllTopics()
        db.session.commit()
        return {'results': [ob.serialize() for ob in topicList]}


@api.route('/<int:topicID>')
@api.doc(params={'topicID': 'ID Number for Topic'})
class api_1_ListTopic(Resource):

    def get(self, topicID):
        """
             Returns Info on a Single Topic
        """
        topicList = topics.topics.query.filter_by(id=topicID).all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in topicList]}