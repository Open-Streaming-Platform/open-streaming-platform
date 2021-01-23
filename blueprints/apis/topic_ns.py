from flask_restplus import Api, Resource, reqparse, Namespace

from classes import topics
from classes.shared import db

api = Namespace('Topic', description='Topic Related Queries and Functions')

@api.route('/topic/')
class api_1_ListTopics(Resource):
    def get(self):
        """
             Returns a List of All Topics
        """
        topicList = topics.topics.query.all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in topicList]}


@api.route('/topic/<int:topicID>')
@api.doc(params={'topicID': 'ID Number for Topic'})
class api_1_ListTopic(Resource):

    def get(self, topicID):
        """
             Returns Info on a Single Topic
        """
        topicList = topics.topics.query.filter_by(id=topicID).all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in topicList]}