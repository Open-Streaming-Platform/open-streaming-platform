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

from functions import system

@socketio.on('newScreenShot')
def newScreenShot(message):

    video = message['loc']
    timeStamp = message['timeStamp']
    videos_root = globalvars.videoRoot + 'videos/'
    videoLocation = None
    thumbnailLocation = None
    channelLocation = None

    if 'clipID' in message:
        video = message['clipID']
        clipQuery = RecordedVideo.Clips.quer.filter_by(id=int(video)).first()
        if clipQuery is not None and clipQuery.recordedVideo.owningUser == current_user.id:
            videoLocation = videos_root + clipQuery.videoLocation
            thumbnailLocation = videos_root + clipQuery.channel.channelLoc + '/tempThumbnail.png'
            channelLocation = clipQuery.channel.channelLoc
    else:
        if video is not None:
            videoQuery = RecordedVideo.RecordedVideo.query.filter_by(id=int(video)).first()
            if videoQuery is not None and videoQuery.owningUser == current_user.id:
                videoLocation = videos_root + videoQuery.videoLocation
                thumbnailLocation = videos_root + videoQuery.channel.channelLoc + '/tempThumbnail.png'
                channelLocation = videoQuery.channel.channelLoc
    if videoLocation is not None and thumbnailLocation is not None and channelLocation is not None:
        try:
            os.remove(thumbnailLocation)
        except OSError:
            pass
        result = subprocess.call(['ffmpeg', '-ss', str(timeStamp), '-i', videoLocation, '-s', '384x216', '-vframes', '1', thumbnailLocation])
        tempLocation = '/videos/' + channelLocation+ '/tempThumbnail.png?dummy=' + str(random.randint(1,50000))
        if 'clip' in message:
            emit('checkClipScreenShot', {'thumbnailLocation': tempLocation, 'timestamp': timeStamp}, broadcast=False)
        else:
            emit('checkScreenShot', {'thumbnailLocation': tempLocation, 'timestamp':timeStamp}, broadcast=False)
    db.session.close()
    db.session.commit()
    db.session.close()
    return 'OK'

@socketio.on('setScreenShot')
def setScreenShot(message):
    timeStamp = message['timeStamp']
    videos_root = globalvars.videoRoot + 'videos/'

    if 'loc' in message:
        video = message['loc']
        if video is not None:
            videoQuery = RecordedVideo.RecordedVideo.query.filter_by(id=int(video)).first()
            if videoQuery is not None and videoQuery.owningUser == current_user.id:
                videoLocation = videos_root + videoQuery.videoLocation
                newThumbnailLocation = videoQuery.videoLocation[:-3] + "png"
                newGifThumbnailLocation = videoQuery.videoLocation[:-3] + "gif"
                videoQuery.thumbnailLocation = newThumbnailLocation
                fullthumbnailLocation = videos_root + newThumbnailLocation
                newGifFullThumbnailLocation = videos_root + newGifThumbnailLocation

                videoQuery.thumbnailLocation = newThumbnailLocation
                videoQuery.gifLocation = newGifThumbnailLocation

                db.session.commit()
                db.session.close()
                try:
                    os.remove(fullthumbnailLocation)
                except OSError:
                    pass
                try:
                    os.remove(newGifFullThumbnailLocation)
                except OSError:
                    pass
                result = subprocess.call(['ffmpeg', '-ss', str(timeStamp), '-i', videoLocation, '-s', '384x216', '-vframes', '1', fullthumbnailLocation])
                gifresult = subprocess.call(['ffmpeg', '-ss', str(timeStamp), '-t', '3', '-i', videoLocation, '-filter_complex', '[0:v] fps=30,scale=w=384:h=-1,split [a][b];[a] palettegen=stats_mode=single [p];[b][p] paletteuse=new=1', '-y', newGifFullThumbnailLocation])

    elif 'clipID' in message:
        clipID = message['clipID']
        clipQuery = RecordedVideo.Clips.query.filter_by(id=int(clipID)).first()
        if clipQuery is not None and current_user.id == clipQuery.recordedVideo.owningUser:
            thumbnailLocation = clipQuery.thumbnailLocation
            fullthumbnailLocation = videos_root + thumbnailLocation
            videoLocation = videos_root + clipQuery.videoLocation
            newClipThumbnail = clipQuery.recordedVideo.channel.channelLoc + '/clips/clip-' + str(clipQuery.id) + '.png'
            fullNewClipThumbnailLocation = videos_root + newClipThumbnail
            clipQuery.thumbnailLocation = newClipThumbnail

            try:
                os.remove(fullthumbnailLocation)
            except OSError:
                pass
            result = subprocess.call(['ffmpeg', '-ss', str(timeStamp), '-i', videoLocation, '-s', '384x216', '-vframes', '1', fullNewClipThumbnailLocation])

            # Generate Gif
            if clipQuery.gifLocation is not None:
                gifLocation = clipQuery.gifLocation
                fullthumbnailLocation = videos_root + gifLocation

                try:
                    os.remove(fullthumbnailLocation)
                except OSError:
                    pass

            newClipThumbnail = clipQuery.recordedVideo.channel.channelLoc + '/clips/clip-' + str(clipQuery.id) + '.gif'
            fullNewClipThumbnailLocation = videos_root + newClipThumbnail
            clipQuery.gifLocation = newClipThumbnail

            db.session.commit()
            db.session.close()

            gifresult = subprocess.call(['ffmpeg', '-ss', str(timeStamp), '-t', '3', '-i', videoLocation, '-filter_complex', '[0:v] fps=30,scale=w=384:h=-1,split [a][b];[a] palettegen=stats_mode=single [p];[b][p] paletteuse=new=1', '-y', fullNewClipThumbnailLocation])

    db.session.commit()
    db.session.close()
    return 'OK'

@socketio.on('saveUploadedThumbnail')
def saveUploadedThumbnailSocketIO(message):
    if current_user.is_authenticated:
        videoID = int(message['videoID'])
        videoQuery = RecordedVideo.RecordedVideo.query.filter_by(id=videoID, owningUser=current_user.id).first()
        if videoQuery is not None:
            thumbnailFilename = message['thumbnailFilename']
            if thumbnailFilename != "" or thumbnailFilename is not None:
                videos_root = globalvars.videoRoot + 'videos/'

                thumbnailPath = videos_root + videoQuery.thumbnailLocation
                shutil.move(current_app.config['VIDEO_UPLOAD_TEMPFOLDER'] + '/' + thumbnailFilename, thumbnailPath)
                db.session.commit()
                db.session.close()
                return 'OK'
            else:
                db.session.commit()
                db.session.close()
                return abort(500)
        else:
            db.session.commit()
            db.session.close()
            return abort(401)
    db.session.commit()
    db.session.close()
    return abort(401)