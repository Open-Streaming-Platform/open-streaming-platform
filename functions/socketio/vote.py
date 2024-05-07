from flask_security import current_user
from flask_socketio import emit

from classes.shared import db, socketio, limiter
from classes import Channel
from classes import Stream
from classes import upvotes
from classes import notifications
from classes import RecordedVideo
from classes import comments

from functions import cachedDbCalls


@socketio.on("getUpvoteTotal")
def handle_upvote_total_request(streamData):
    loc = streamData["loc"]
    vidType = str(streamData["vidType"])

    myUpvote = False
    totalUpvotes = 0

    totalQuery = None
    myVoteQuery = None

    if vidType == "stream":
        loc = str(loc)
        channelQuery = cachedDbCalls.getChannelByLoc(loc)
        streamQuery = Stream.Stream.query.filter_by(linkedChannel=channelQuery.id).with_entities(Stream.Stream.id).first()
        if streamQuery != None:
            totalQuery = upvotes.streamUpvotes.query.filter_by(
                streamID=streamQuery.id
            ).count()
            try:
                myVoteQuery = upvotes.streamUpvotes.query.filter_by(
                    userID=current_user.id, streamID=streamQuery.id
                ).first()
            except:
                pass

    elif vidType == "video":
        loc = int(loc)
        totalQuery = upvotes.videoUpvotes.query.filter_by(videoID=loc).count()
        try:
            myVoteQuery = upvotes.videoUpvotes.query.filter_by(
                userID=current_user.id, videoID=loc
            ).first()
        except:
            pass
    elif vidType == "comment":
        loc = int(loc)
        totalQuery = upvotes.commentUpvotes.query.filter_by(commentID=loc).count()
        try:
            myVoteQuery = upvotes.commentUpvotes.query.filter_by(
                userID=current_user.id, commentID=loc
            ).first()
        except:
            pass
    elif vidType == "clip":
        loc = int(loc)
        totalQuery = upvotes.clipUpvotes.query.filter_by(clipID=loc).count()
        try:
            myVoteQuery = upvotes.clipUpvotes.query.filter_by(
                userID=current_user.id, clipID=loc
            ).first()
        except:
            pass

    if totalQuery is not None:
        totalUpvotes = totalQuery
    if myVoteQuery is not None:
        myUpvote = True

    db.session.commit()
    db.session.close()
    emit(
        "upvoteTotalResponse",
        {
            "totalUpvotes": str(totalUpvotes),
            "myUpvote": str(myUpvote),
            "type": vidType,
            "loc": loc,
        },
    )
    return "OK"


@socketio.on("changeUpvote")
@limiter.limit("10/minute")
def handle_upvoteChange(streamData):
    loc = streamData["loc"]
    vidType = str(streamData["vidType"])

    myUpvote = False
    totalUpvotes = 0

    totalQuery = None
    myVoteQuery = None

    if vidType == "stream":
        loc = str(loc)
        channelQuery = cachedDbCalls.getChannelByLoc(loc)
        streamQuery = Stream.Stream.query.filter_by(linkedChannel=channelQuery.id).with_entities(
            Stream.Stream.id).first()
        if streamQuery != None:
            stream = streamQuery
            myVoteQuery = upvotes.streamUpvotes.query.filter_by(
                userID=current_user.id, streamID=stream.id
            ).first()

            if myVoteQuery is None:
                newUpvote = upvotes.streamUpvotes(current_user.id, stream.id)
                db.session.add(newUpvote)

                # Create Notification for Channel Owner on New Like
                newNotification = notifications.userNotification(
                    current_user.username
                    + " liked your live stream - "
                    + channelQuery.channelName,
                    "/view/" + str(channelQuery.channelLoc),
                    "/images/" + str(current_user.pictureLocation),
                    channelQuery.owningUser,
                )
                db.session.add(newNotification)

            else:
                db.session.delete(myVoteQuery)

            totalQuery = upvotes.streamUpvotes.query.filter_by(
                streamID=stream.id
            ).count()
            myVoteQuery = upvotes.streamUpvotes.query.filter_by(
                userID=current_user.id, streamID=stream.id
            ).first()

            db.session.commit()

    elif vidType == "video":
        loc = int(loc)
        videoQuery = cachedDbCalls.getVideo(loc).first()
        if videoQuery is not None:
            myVoteQuery = upvotes.videoUpvotes.query.filter_by(
                userID=current_user.id, videoID=loc
            ).first()

            if myVoteQuery is None:
                newUpvote = upvotes.videoUpvotes(current_user.id, loc)
                db.session.add(newUpvote)

                # Create Notification for Video Owner on New Like
                newNotification = notifications.userNotification(
                    current_user.username
                    + " liked your video - "
                    + videoQuery.channelName,
                    "/play/" + str(videoQuery.id),
                    "/images/" + str(current_user.pictureLocation),
                    videoQuery.owningUser,
                )
                db.session.add(newNotification)

            else:
                db.session.delete(myVoteQuery)

            totalQuery = upvotes.videoUpvotes.query.filter_by(videoID=loc).count()
            myVoteQuery = upvotes.videoUpvotes.query.filter_by(
                userID=current_user.id, videoID=loc
            ).first()

            db.session.commit()

    elif vidType == "comment":
        loc = int(loc)
        videoCommentQuery = comments.videoComments.query.filter_by(id=loc).first()
        if videoCommentQuery is not None:
            myVoteQuery = upvotes.commentUpvotes.query.filter_by(
                userID=current_user.id, commentID=videoCommentQuery.id
            ).first()
            if myVoteQuery is None:
                newUpvote = upvotes.commentUpvotes(
                    current_user.id, videoCommentQuery.id
                )
                db.session.add(newUpvote)

                # Create Notification for Video Owner on New Like
                newNotification = notifications.userNotification(
                    current_user.username + " liked your comment on a video",
                    "/play/" + str(videoCommentQuery.videoID),
                    "/images/" + str(current_user.pictureLocation),
                    videoCommentQuery.userID,
                )
                db.session.add(newNotification)

            else:
                db.session.delete(myVoteQuery)

            totalQuery = upvotes.commentUpvotes.query.filter_by(commentID=loc).count()
            myVoteQuery = upvotes.commentUpvotes.query.filter_by(
                userID=current_user.id, commentID=loc
            ).first()

            db.session.commit()

    elif vidType == "clip":
        loc = int(loc)
        clipQuery = RecordedVideo.Clips.query.filter_by(id=loc).first()
        if clipQuery is not None:
            myVoteQuery = upvotes.clipUpvotes.query.filter_by(
                userID=current_user.id, clipID=loc
            ).first()

            if myVoteQuery is None:
                newUpvote = upvotes.clipUpvotes(current_user.id, loc)
                db.session.add(newUpvote)

                # Create Notification for Clip Owner on New Like
                newNotification = notifications.userNotification(
                    current_user.username + " liked your clip - " + clipQuery.clipName,
                    "/clip/" + str(clipQuery.id),
                    "/images/" + str(current_user.pictureLocation),
                    clipQuery.owningUser,
                )
                db.session.add(newNotification)

            else:
                db.session.delete(myVoteQuery)

            totalQuery = upvotes.clipUpvotes.query.filter_by(clipID=loc).count()
            myVoteQuery = upvotes.clipUpvotes.query.filter_by(
                userID=current_user.id, clipID=loc
            ).first()

            db.session.commit()

    if totalQuery is not None:
        totalUpvotes = totalQuery
    if myVoteQuery is not None:
        myUpvote = True

    db.session.close()
    emit(
        "upvoteTotalResponse",
        {
            "totalUpvotes": str(totalUpvotes),
            "myUpvote": str(myUpvote),
            "type": vidType,
            "loc": loc,
        },
    )
    return "OK"
