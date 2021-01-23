from flask_restplus import Api, Resource, reqparse, Namespace
from flask import request
from os import path, remove

from classes import RecordedVideo
from classes import apikey
from classes import topics
from classes import views
from classes import upvotes
from classes.shared import db

from globals import globalvars

api = Namespace('Video', description='Video Related Queries and Functions')

videoParserPut = reqparse.RequestParser()
videoParserPut.add_argument('videoName', type=str)
videoParserPut.add_argument('description', type=str)
videoParserPut.add_argument('topicID', type=int)

@api.route('/video/')
class api_1_ListVideos(Resource):
    def get(self):
        """
             Returns a List of All Recorded Videos
        """
        videoList = RecordedVideo.RecordedVideo.query.filter_by(pending=False, published=True).all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in videoList]}


@api.route('/video/<int:videoID>')
@api.doc(params={'videoID': 'ID Number for the Video'})
class api_1_ListVideo(Resource):
    def get(self, videoID):
        """
             Returns Info on a Single Recorded Video
        """
        videoList = RecordedVideo.RecordedVideo.query.filter_by(id=videoID, published=True).all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in videoList]}

    @api.expect(videoParserPut)
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def put(self, videoID):
        """
            Change a Video's Name, Description, or Topic
        """
        if 'X-API-KEY' in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(key=request.headers['X-API-KEY']).first()
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    videoQuery = RecordedVideo.RecordedVideo.query.filter_by(id=int(videoID)).first()
                    if videoQuery is not None:
                        if videoQuery.owningUser == requestAPIKey.userID:
                            args = videoParserPut.parse_args()
                            if 'videoName' in args:
                                if args['videoName'] is not None:
                                    videoQuery.channelName = args['videoName']
                            if 'topicID' in args:
                                if args['topicID'] is not None:
                                    possibleTopics = topics.topics.query.filter_by(id=int(args['topicID'])).first()
                                    if possibleTopics is not None:
                                        videoQuery.topic = int(args['topicID'])
                            if 'description' in args:
                                if args['description'] is not None:
                                    videoQuery.description = args['description']
                            db.session.commit()
                            return {'results': {'message': 'Video Updated'}}, 200
        return {'results': {'message': 'Request Error'}}, 400

    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def delete(self, videoID):
        """
            Deletes a Video
        """
        if 'X-API-KEY' in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(key=request.headers['X-API-KEY']).first()
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    videoQuery = RecordedVideo.RecordedVideo.query.filter_by(id=videoID).first()
                    if videoQuery is not None:
                        if videoQuery.owningUser == requestAPIKey.userID:
                            videos_root = globalvars.videoRoot + 'videos/'

                            filePath = videos_root + videoQuery.videoLocation
                            thumbnailPath = videos_root + videoQuery.videoLocation[:-4] + ".png"

                            if filePath != videos_root:
                                if path.exists(filePath) and (
                                        videoQuery.videoLocation is not None or videoQuery.videoLocation != ""):
                                    remove(filePath)
                                    if path.exists(thumbnailPath):
                                        remove(thumbnailPath)
                            upvoteQuery = upvotes.videoUpvotes.query.filter_by(videoID=videoQuery.id).all()
                            for vote in upvoteQuery:
                                db.session.delete(vote)
                            vidComments = videoQuery.comments
                            for comment in vidComments:
                                db.session.delete(comment)
                            vidViews = views.views.query.filter_by(viewType=1, itemID=videoQuery.id)
                            for view in vidViews:
                                db.session.delete(view)
                            db.session.delete(videoQuery)
                            db.session.commit()
                            return {'results': {'message': 'Video Deleted'}}, 200
        return {'results': {'message': 'Request Error'}}, 400