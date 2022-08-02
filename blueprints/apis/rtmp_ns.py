from flask_restx import Api, Resource, reqparse, Namespace
from flask import request
import datetime
import socket
import hashlib
import logging

from classes import settings
from classes import Channel
from classes import Sec
from classes.shared import db

from functions import rtmpFunc
from functions import system
from functions import securityFunc

log = logging.getLogger("app.blueprints.apis.rtmp_ns")

def checkRTMPAuthIP(requestData):
    authorized = False
    rtmpServerID = None
    requestIP = "0.0.0.0"
    if requestData.environ.get("HTTP_X_FORWARDED_FOR") is None:
        requestIP = requestData.environ["REMOTE_ADDR"]
    else:
        requestIP = requestData.environ["HTTP_X_FORWARDED_FOR"]

    authorizedRTMPServers = settings.rtmpServer.query.with_entities(
        settings.rtmpServer.id, settings.rtmpServer.active, settings.rtmpServer.address
    ).all()

    receivedIP = requestIP
    ipList = requestIP.split(",")
    confirmedIP = ""
    for ip in ipList:
        parsedip = ip.strip()
        for server in authorizedRTMPServers:
            if authorized is False:
                if server.active is True:
                    resolveResults = socket.getaddrinfo(server.address, 0)
                    for resolved in resolveResults:
                        if parsedip == resolved[4][0]:
                            authorized = True
                            confirmedIP = resolved[4][0]
                            rtmpServerID = server.id

    if authorized is False:
        confirmedIP = receivedIP
        system.newLog(1, "Unauthorized RTMP Server - " + confirmedIP)

    return (authorized, confirmedIP, rtmpServerID)


api = Namespace("rtmp", description="RTMP Related Queries and Functions")

rtmpStage1Auth = reqparse.RequestParser()
rtmpStage1Auth.add_argument("name", type=str)
rtmpStage1Auth.add_argument("addr", type=str)

rtmpStage2Auth = reqparse.RequestParser()
rtmpStage2Auth.add_argument("name", type=str)
rtmpStage2Auth.add_argument("addr", type=str)

rtmpRecCheck = reqparse.RequestParser()
rtmpRecCheck.add_argument("name", type=str)

rtmpStreamClose = reqparse.RequestParser()
rtmpStreamClose.add_argument("name", type=str)
rtmpStreamClose.add_argument("addr", type=str)

rtmpRecClose = reqparse.RequestParser()
rtmpRecClose.add_argument("name", type=str)
rtmpRecClose.add_argument("path", type=str)

rtmpAuthCheck = reqparse.RequestParser()
rtmpAuthCheck.add_argument("name", type=str)
rtmpAuthCheck.add_argument("addr", type=str)
rtmpAuthCheck.add_argument("username", type=str)
rtmpAuthCheck.add_argument("hash", type=str)


@api.route("/stage1")
@api.doc(
    params={
        "name": "Stream Key of Channel",
        "addr": "IP Address of Endpoint Making Request",
    }
)
class api_1_rtmp_stage1(Resource):
    @api.expect(rtmpStage1Auth)
    @api.doc(responses={200: "Success", 400: "Request Error"})
    def post(self):
        """
        Initialize Stage 1 of RTMP Authentication
        """
        # Perform RTMP IP Authorization Check
        authorized = checkRTMPAuthIP(request)
        if authorized[0] is False:
            log.warning({"level": "warning", "message": "Unauthorized RTMP Server - " + authorized[1]})
            return {
                "results": {"message": "Unauthorized RTMP Server - " + authorized[1]}
            }, 400

        args = rtmpStage1Auth.parse_args()

        if "name" in args and "addr" in args:
            name = args["name"]
            addr = args["addr"]
            results = rtmpFunc.rtmp_stage1_streamkey_check(name, addr)
            if results["success"] is True:
                log.info({"level": "info", "message": "Stage 1 Auth Complete - " + results['channelLoc']})
                return {"results": results}, 200
            else:
                log.warning({"level": "warning", "message": "Stage 1 Auth Failed - " + results['channelLoc']})
                return {"results": results}, 400
        else:
            log.warning({"level": "warning", "message": "Stage 1 Auth Failed - Missing Required Data"})
            return {
                "results": {
                    "time": str(datetime.datetime.utcnow()),
                    "request": "Stage1",
                    "success": False,
                    "channelLoc": None,
                    "type": None,
                    "ipAddress": None,
                    "message": "Invalid Request",
                }
            }, 400


@api.route("/stage2")
@api.doc(
    params={
        "name": "Channel Location of Channel Processed Under Stage 1",
        "addr": "IP Address of Endpoint Making Request",
    }
)
class api_1_rtmp_stage2(Resource):
    @api.expect(rtmpStage2Auth)
    @api.doc(responses={200: "Success", 400: "Request Error"})
    def post(self):
        """
        Initialize Stage 2 of RTMP Authentication
        """

        # Perform RTMP IP Authorization Check
        authorized = checkRTMPAuthIP(request)
        if authorized[0] is False:
            log.warning({"level": "warning", "message": "Unauthorized RTMP Server - " + authorized[1]})
            return {
                "results": {"message": "Unauthorized RTMP Server - " + authorized[1]}
            }, 400

        args = rtmpStage2Auth.parse_args()

        if "name" in args and "addr" in args:
            name = args["name"]
            addr = args["addr"]
            rtmpServer = authorized[2]
            results = rtmpFunc.rtmp_stage2_user_auth_check(name, addr, rtmpServer)
            if results["success"] is True:
                log.info({"level": "info", "message": "Stage 2 Auth Complete - " + results['channelLoc']})
                return {"results": results}, 200
            else:
                log.warning({"level": "warning", "message": "Stage 2 Auth Failed - " + results['channelLoc']})
                return {"results": results}, 400
        else:
            log.warning({"level": "warning", "message": "Stage 2 Auth Failed - Missing Required Data"})
            return {
                "results": {
                    "time": str(datetime.datetime.utcnow()),
                    "request": "Stage2",
                    "success": False,
                    "channelLoc": None,
                    "type": None,
                    "ipAddress": None,
                    "message": "Invalid Request",
                }
            }, 400


@api.route("/reccheck")
@api.doc(params={"name": "Stream Key of Channel"})
class api_1_rtmp_reccheck(Resource):
    @api.expect(rtmpRecCheck)
    @api.doc(responses={200: "Success", 400: "Request Error"})
    def post(self):
        """
        Initialize Recording Check for RTMP
        """

        # Perform RTMP IP Authorization Check
        authorized = checkRTMPAuthIP(request)
        if authorized[0] is False:
            log.warning({"level": "warning", "message": "Unauthorized RTMP Server - " + authorized[1]})
            return {
                "results": {"message": "Unauthorized RTMP Server - " + authorized[1]}
            }, 400

        args = rtmpRecCheck.parse_args()

        if "name" in args:
            name = args["name"]
            results = rtmpFunc.rtmp_record_auth_check(name)
            if results["success"] is True:
                log.info({"level": "info", "message": "Recording Auth Complete - " + results['channelLoc']})
                return {"results": results}, 200
            else:
                log.warning({"level": "warning", "message": "Recording Auth Failed - " + results['channelLoc']})
                return {"results": results}, 400
        else:
            log.warning({"level": "warning", "message": "Recording Auth Failed - Missing Required Data"})
            return {
                "results": {
                    "time": str(datetime.datetime.utcnow()),
                    "request": "RecordCheck",
                    "success": False,
                    "channelLoc": None,
                    "type": None,
                    "ipAddress": None,
                    "message": "Invalid Request",
                }
            }, 400


@api.route("/streamclose")
@api.doc(
    params={
        "name": "Stream Key of Channel",
        "addr": "IP Address of Endpoint Making Request",
    }
)
class api_1_rtmp_streamclose(Resource):
    @api.expect(rtmpStreamClose)
    @api.doc(responses={200: "Success", 400: "Request Error"})
    def post(self):
        """
        Close an Open Stream
        """

        # Perform RTMP IP Authorization Check
        authorized = checkRTMPAuthIP(request)
        if authorized[0] is False:
            return {
                "results": {"message": "Unauthorized RTMP Server -" + authorized[1]}
            }, 400

        args = rtmpStreamClose.parse_args()

        if "name" in args and "addr" in args:
            name = args["name"]
            addr = args["addr"]
            results = rtmpFunc.rtmp_user_deauth_check(name, addr)
            if results["success"] is True:
                return {"results": results}, 200
            else:
                return {"results": results}, 400
        else:
            return {
                "results": {
                    "time": str(datetime.datetime.utcnow()),
                    "request": "StreamClose",
                    "success": False,
                    "channelLoc": None,
                    "type": None,
                    "ipAddress": None,
                    "message": "Invalid Request",
                }
            }, 400


@api.route("/recclose")
@api.doc(
    params={
        "name": "Channel Location of Video to Close",
        "path": "Nginx-rtmp Full Path of Preprocessed Video",
    }
)
class api_1_rtmp_recclose(Resource):
    @api.expect(rtmpRecClose)
    @api.doc(responses={200: "Success", 400: "Request Error"})
    def post(self):
        """
        Finalize Processing of a Recorded Video
        """

        # Perform RTMP IP Authorization Check
        authorized = checkRTMPAuthIP(request)
        if authorized[0] is False:
            return {
                "results": {"message": "Unauthorized RTMP Server - " + authorized[1]}
            }, 400

        args = rtmpRecClose.parse_args()

        if "name" in args and "path" in args:
            name = args["name"]
            path = args["path"]
            results = rtmpFunc.rtmp_rec_Complete_handler.delay(name, path)

            return {
                "results": {
                    "time": str(datetime.datetime.utcnow()),
                    "request": "RecordingClose",
                    "success": True,
                    "channelLoc": name,
                    "type": "video",
                    "message": "Recording Queued for Closing",
                }
            }, 200

        else:
            return {
                "results": {
                    "time": str(datetime.datetime.utcnow()),
                    "request": "RecordingClose",
                    "success": False,
                    "channelLoc": None,
                    "type": None,
                    "ipAddress": None,
                    "message": "Invalid Request",
                }
            }, 400


@api.route("/playbackauth")
@api.doc(
    params={
        "name": "Stream Location ID",
        "addr": "Client IP Address",
        "username": "Requesting Username",
        "hash": "OSP Generated Security Hash for User and Stream",
    }
)
class api_1_rtmp_playbackauth(Resource):
    @api.expect(rtmpAuthCheck)
    @api.doc(responses={200: "Success", 400: "Request Error"})
    def post(self):
        """
        Validate playback of a direct RTMP Stream
        """
        args = rtmpAuthCheck.parse_args()
        stream = args["name"]
        clientIP = args["addr"]

        if clientIP == "127.0.0.1" or clientIP == "localhost":
            return "OK"
        else:
            streamQuery = (
                Channel.Channel.query.filter_by(channelLoc=stream)
                .with_entities(
                    Channel.Channel.id,
                    Channel.Channel.channelLoc,
                    Channel.Channel.owningUser,
                    Channel.Channel.protected,
                )
                .first()
            )
            if streamQuery is not None:

                if streamQuery.protected is False:
                    db.session.close()
                    return {"results": True}, 200
                else:
                    username = args["username"]
                    secureHash = args["hash"]

                    if streamQuery is not None:
                        requestedUser = Sec.User.query.filter_by(
                            username=username
                        ).first()
                        if requestedUser is not None:
                            isValid = False
                            validHash = None
                            if requestedUser.authType == 0:
                                validHash = hashlib.sha256(
                                    (
                                        requestedUser.username
                                        + streamQuery.channelLoc
                                        + requestedUser.password
                                    ).encode("utf-8")
                                ).hexdigest()
                            else:
                                validHash = hashlib.sha256(
                                    (
                                        requestedUser.username
                                        + streamQuery.channelLoc
                                        + requestedUser.oAuthID
                                    ).encode("utf-8")
                                ).hexdigest()
                            if secureHash == validHash:
                                isValid = True
                            if isValid is True:
                                if streamQuery.owningUser == requestedUser.id:
                                    db.session.close()
                                    return {"results": True}, 200
                                else:
                                    if securityFunc.check_isUserValidRTMPViewer(
                                        requestedUser.id, streamQuery.id
                                    ):
                                        db.session.close()
                                        return {"results": True}, 200
        db.session.close()
        return {"results": False}, 400
