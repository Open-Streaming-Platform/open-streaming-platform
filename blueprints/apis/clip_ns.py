from flask_restx import Api, Resource, reqparse, Namespace
from flask import request
from os import path, remove

from classes import RecordedVideo
from classes import apikey
from classes import upvotes
from classes.shared import db

from functions import cachedDbCalls, videoFunc, templateFilters
from functions.scheduled_tasks import video_tasks

from globals import globalvars

api = Namespace("clip", description="Clip Related Queries and Functions")

clipParserPut = reqparse.RequestParser()
clipParserPut.add_argument("clipName", type=str)
clipParserPut.add_argument("description", type=str)

clipSearchPost = reqparse.RequestParser()
clipSearchPost.add_argument("term", type=str)


@api.route("/")
class api_1_ListClips(Resource):
    def get(self):
        """
        Returns a List of All Saved Clips
        """
        clipsList = RecordedVideo.Clips.query.filter_by(published=True).all()
        db.session.commit()
        return {
            "results": [
                ob.serialize()
                for ob in clipsList
                if ob.recordedVideo.channel.private is False
            ]
        }


@api.route("/<int:clipID>")
@api.doc(params={"clipID": "ID Number for the Clip"})
class api_1_ListClip(Resource):
    def get(self, clipID):
        """
        Returns Info on a Single Saved Clip
        """
        clipList = RecordedVideo.Clips.query.filter_by(id=clipID, published=True).all()
        db.session.commit()
        return {
            "results": [
                ob.serialize()
                for ob in clipList
                if ob.recordedVideo.channel.private is False
            ]
        }

    @api.expect(clipParserPut)
    @api.doc(security="apikey")
    @api.doc(responses={200: "Success", 400: "Request Error"})
    def put(self, clipID):
        """
        Change a Clip's Name or Description
        """
        if "X-API-KEY" in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(
                key=request.headers["X-API-KEY"]
            ).first()
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    clipQuery = RecordedVideo.Clips.query.filter_by(
                        id=int(clipID)
                    ).first()
                    if clipQuery is not None:
                        if clipQuery.recordedVideo.owningUser == requestAPIKey.userID:
                            args = clipParserPut.parse_args()
                            if "clipName" in args:
                                if args["clipName"] is not None:
                                    clipQuery.clipName = args["clipName"]
                            if "description" in args:
                                if args["description"] is not None:
                                    clipQuery.description = args["description"]
                            db.session.commit()
                            return {"results": {"message": "Clip Updated"}}, 200
        return {"results": {"message": "Request Error"}}, 400

    @api.doc(security="apikey")
    @api.doc(responses={200: "Success", 400: "Request Error"})
    def delete(self, clipID):
        """
        Deletes a Clip
        """
        if "X-API-KEY" in request.headers:
            requestAPIKey = apikey.apikey.query.filter_by(
                key=request.headers["X-API-KEY"]
            ).first()
            if requestAPIKey is not None:
                if requestAPIKey.isValid():
                    clipQuery = RecordedVideo.Clips.query.filter_by(id=clipID).first()
                    if clipQuery is not None:
                        if clipQuery.recordedVideo.owningUser == requestAPIKey.userID:
                            results = video_tasks.delete_video_clip.delay(clipQuery.id)
                            return {
                                "results": {"message": "Clip Scheduled for Deletion"}
                            }, 200
        return {"results": {"message": "Request Error"}}, 400


@api.route("/search")
class api_1_SearchClips(Resource):
    # Clips - Search Clipped Video
    @api.expect(clipSearchPost)
    @api.doc(responses={200: "Success", 400: "Request Error"})
    def post(self):
        """
        Searches Video Names and Metadata and returns Name and Link
        """
        args = clipSearchPost.parse_args()
        returnArray = []
        if "term" in args:
            finalArray = []
            returnArray = cachedDbCalls.searchClips(args["term"])
            for clip in returnArray:
                newVidObj = [clip.id, clip.clipName, clip.uuid, clip.thumbnailLocation]
                finalArray.append(newVidObj)
            return {"results": finalArray}
        else:
            return {"results": {"message": "Request Error"}}, 400
