from flask_restplus import Api, Resource, reqparse, Namespace
from flask import request
import werkzeug
from os import path, remove

from classes import RecordedVideo
from classes import apikey
from classes import topics
from classes import views
from classes.shared import db

from functions import cachedDbCalls
from functions.scheduled_tasks import video_tasks

api = Namespace('video', description='Video Related Queries and Functions')

videoParserPut = reqparse.RequestParser()
videoParserPut.add_argument('videoName', type=str)
videoParserPut.add_argument('description', type=str)
videoParserPut.add_argument('topicID', type=int)

videoSearchPost = reqparse.RequestParser()
videoSearchPost.add_argument('term', type=str, required=True)

file_upload = reqparse.RequestParser()
file_upload.add_argument('video_file',
                         type=werkzeug.datastructures.FileStorage,
                         location='files',
                         required=True,
                         help='MP4 file')
file_upload.add_argument('channelId', type=int, required=True)

@api.route('/')
class api_1_ListVideos(Resource):
    def get(self):
        """
             Returns a List of All Recorded Videos
        """
        videoList = RecordedVideo.RecordedVideo.query.filter_by(pending=False, published=True).all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in videoList if ob.channel.private is False]}

    @api.expect(file_upload)
    @api.expect(videoParserPut)
    @api.doc(security='apikey')
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def post(self):
        """
        Upload a Video to a Channel via API
        """
        if 'X-API-KEY' in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(key=request.headers['X-API-KEY']).first()
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    args = file_upload.parse_args()
                    if args['video_file'].mimetype == 'video/mp4':
                        destination = '/var/www/videos/temp/'
                    else:
                        db.session.commit()
                        abort(400)
                    db.session.commit()
                    return {'status': 'Done'}

@api.route('/<int:videoID>')
@api.doc(params={'videoID': 'ID Number for the Video'})
class api_1_ListVideo(Resource):
    def get(self, videoID):
        """
             Returns Info on a Single Recorded Video
        """
        videoList = RecordedVideo.RecordedVideo.query.filter_by(id=videoID, published=True).all()
        db.session.commit()
        return {'results': [ob.serialize() for ob in videoList if ob.channel.private is False]}

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
                            results = video_tasks.delete_video.delay(videoQuery.id)
                            return {'results': {'message': 'Video Queued for Deletion'}}, 200
        return {'results': {'message': 'Request Error'}}, 400

@api.route('/search')
class api_1_SearchVideos(Resource):
    # Video - Search Recorded Video
    @api.expect(videoSearchPost)
    @api.doc(responses={200: 'Success', 400: 'Request Error'})
    def post(self):
        """
            Searches Video Names and Metadata and returns Name and Link
        """
        args = videoSearchPost.parse_args()
        returnArray = []
        if 'term' in args:
            finalArray = []
            returnArray = cachedDbCalls.searchVideos(args['term'])
            for vid in returnArray:
                newVidObj = [vid.id, vid.channelName, vid.uuid, vid.thumbnailLocation]
                finalArray.append(newVidObj)
            return {'results': finalArray}
        else:
            return {'results': {'message': 'Request Error'}}, 400