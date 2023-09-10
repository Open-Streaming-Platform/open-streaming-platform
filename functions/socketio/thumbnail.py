import psutil
import os
import time
import subprocess
import random
import shutil
from flask import abort, current_app
from flask_socketio import emit
from flask_security import current_user
from sqlalchemy.sql.expression import func

from classes.shared import db, socketio, limiter
from classes import Sec
from classes import settings
from classes import RecordedVideo
from classes import Stream

from globals import globalvars

from functions import system, cachedDbCalls, templateFilters
from functions.scheduled_tasks import video_tasks


@socketio.on("newScreenShot")
def newScreenShot(message):

    video = message["loc"]
    timeStamp = message["timeStamp"]
    videos_root = globalvars.videoRoot + "videos/"
    videoLocation = None
    thumbnailLocation = None
    channelLocation = None

    if "clipID" in message:
        video = message["clipID"]
        clipQuery = RecordedVideo.Clips.query.filter_by(id=int(video)).first()
        if clipQuery is not None and (
            clipQuery.recordedVideo.owningUser == current_user.id
            or current_user.has_role("Admin")
        ):
            videoLocation = videos_root + clipQuery.videoLocation
            thumbnailLocation = (
                videos_root
                + clipQuery.recordedVideo.channel.channelLoc
                + "/tempThumbnail.png"
            )
            channelLocation = clipQuery.recordedVideo.channel.channelLoc
    else:
        if video is not None:
            videoQuery = cachedDbCalls.getVideo(int(video))
            if videoQuery is not None and (
                videoQuery.owningUser == current_user.id
                or current_user.has_role("Admin")
            ):
                channelQuery = cachedDbCalls.getChannel(videoQuery.channelID)
                videoLocation = videos_root + videoQuery.videoLocation
                thumbnailLocation = (
                    videos_root + channelQuery.channelLoc + "/tempThumbnail.png"
                )
                channelLocation = channelQuery.channelLoc
    if (
        videoLocation is not None
        and thumbnailLocation is not None
        and channelLocation is not None
    ):
        try:
            os.remove(thumbnailLocation)
        except OSError:
            pass
        result = subprocess.call(
            [
                "/usr/bin/ffmpeg",
                "-ss",
                str(timeStamp),
                "-i",
                videoLocation,
                "-s",
                "384x216",
                "-vframes",
                "1",
                thumbnailLocation,
            ]
        )
        tempLocation = (
            "/videos/"
            + channelLocation
            + "/tempThumbnail.png?dummy="
            + str(random.randint(1, 50000))
        )
        if "clip" in message:
            emit(
                "checkClipScreenShot",
                {"thumbnailLocation": tempLocation, "timestamp": timeStamp},
                broadcast=False
            )
        else:
            emit(
                "checkScreenShot",
                {"thumbnailLocation": tempLocation, "timestamp": timeStamp},
                broadcast=False
            )
    db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("setScreenShot")
def setScreenShot(message):
    timeStamp = message["timeStamp"]
    videos_root = globalvars.videoRoot + "videos/"

    if "loc" in message:
        video = message["loc"]
        if video is not None:
            videoQuery = cachedDbCalls.getVideo(video)
            if videoQuery is not None and (
                videoQuery.owningUser == current_user.id
                or current_user.has_role("Admin")
            ):
                # Offloads Video Thumbnail Creation to Task Queue
                video_tasks.update_video_thumbnail.delay(videoQuery.id, timeStamp)

    elif "clipID" in message:
        clipID = message["clipID"]
        clipQuery = RecordedVideo.Clips.query.filter_by(id=int(clipID)).first()
        if clipQuery is not None and (
            current_user.id == clipQuery.recordedVideo.owningUser
            or current_user.has_role("Admin")
        ):
            thumbnailLocation = clipQuery.thumbnailLocation
            fullthumbnailLocation = videos_root + thumbnailLocation
            videoLocation = videos_root + clipQuery.videoLocation
            newClipThumbnail = (
                clipQuery.recordedVideo.channel.channelLoc
                + "/clips/clip-"
                + str(clipQuery.id)
                + ".png"
            )
            fullNewClipThumbnailLocation = videos_root + newClipThumbnail
            clipQuery.thumbnailLocation = newClipThumbnail

            try:
                os.remove(fullthumbnailLocation)
            except OSError:
                pass
            result = subprocess.call(
                [
                    "/usr/bin/ffmpeg",
                    "-ss",
                    str(timeStamp),
                    "-i",
                    videoLocation,
                    "-s",
                    "384x216",
                    "-vframes",
                    "1",
                    fullNewClipThumbnailLocation,
                ]
            )

            # Generate Gif
            if clipQuery.gifLocation is not None:
                gifLocation = clipQuery.gifLocation
                fullthumbnailLocation = videos_root + gifLocation

                try:
                    os.remove(fullthumbnailLocation)
                except OSError:
                    pass

            newClipThumbnail = (
                clipQuery.recordedVideo.channel.channelLoc
                + "/clips/clip-"
                + str(clipQuery.id)
                + ".gif"
            )
            fullNewClipThumbnailLocation = videos_root + newClipThumbnail
            clipQuery.gifLocation = newClipThumbnail

            db.session.commit()
            db.session.close()

            gifresult = subprocess.call(
                [
                    "/usr/bin/ffmpeg",
                    "-ss",
                    str(timeStamp),
                    "-t",
                    "3",
                    "-i",
                    videoLocation,
                    "-filter_complex",
                    "[0:v] fps=30,scale=w=384:h=-1,split [a][b];[a] palettegen=stats_mode=single [p];[b][p] paletteuse=new=1",
                    "-y",
                    fullNewClipThumbnailLocation,
                ]
            )

    db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("saveUploadedThumbnail")
def saveUploadedThumbnailSocketIO(message):
    if current_user.is_authenticated:
        if "videoID" in message:
            videoID = int(message["videoID"])
            videoQuery = cachedDbCalls.getVideo(videoID)
            if videoQuery is not None and videoQuery.owningUser == current_user.id:
                thumbnailFilename = message["thumbnailFilename"]
                if thumbnailFilename != "" or thumbnailFilename is not None:
                    videos_root = globalvars.videoRoot + "videos/"

                    thumbnailPath = videos_root + videoQuery.thumbnailLocation
                    shutil.move(
                        current_app.config["VIDEO_UPLOAD_TEMPFOLDER"]
                        + "/"
                        + thumbnailFilename,
                        thumbnailPath,
                    )
                    db.session.commit()
                    db.session.close()
                    return "OK"
                else:
                    db.session.commit()
                    db.session.close()
                    return abort(500)
            else:
                db.session.commit()
                db.session.close()
                return abort(401)
        if "clipID" in message:
            clipID = int(message["clipID"])
            clipQuery = RecordedVideo.Clips.query.filter_by(id=clipID).first()
            if (
                clipQuery is not None
                and clipQuery.recordedVideo.owningUser == current_user.id
            ):
                thumbnailFilename = message["thumbnailFilename"]
                if thumbnailFilename != "" or thumbnailFilename is not None:
                    videos_root = globalvars.videoRoot + "videos/"
                    newClipThumbnail = (
                        clipQuery.recordedVideo.channel.channelLoc
                        + "/clips/clip-"
                        + str(clipQuery.id)
                        + ".png"
                    )
                    thumbnailPath = videos_root + newClipThumbnail
                    shutil.move(
                        current_app.config["VIDEO_UPLOAD_TEMPFOLDER"]
                        + "/"
                        + thumbnailFilename,
                        thumbnailPath,
                    )
                    db.session.commit()
                    db.session.close()
                    return "OK"
                else:
                    db.session.commit()
                    db.session.close()
                    return abort(500)
            else:
                db.session.commit()
                db.session.close()
                return abort(500)
    db.session.commit()
    db.session.close()
    return abort(401)
