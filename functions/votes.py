from flask_security import current_user
from classes.shared import db

from classes import upvotes

def get_Video_Upvotes(videoID):
    videoUpVotesQuery = upvotes.videoUpvotes.query.filter_by(videoID=videoID).count()
    result = videoUpVotesQuery
    db.session.close()
    return result

def get_Stream_Upvotes(videoID):
    videoUpVotesQuery = upvotes.streamUpvotes.query.filter_by(streamID=videoID).count()
    result = videoUpVotesQuery
    db.session.close()
    return result

def get_Clip_Upvotes(videoID):
    videoUpVotesQuery = upvotes.clipUpvotes.query.filter_by(clipID=videoID).count()
    result = videoUpVotesQuery
    db.session.close()
    return result

def check_isCommentUpvoted(commentID):
    if current_user.is_authenticated:
        commentQuery = upvotes.commentUpvotes.query.filter_by(commentID=int(commentID), userID=current_user.id).first()
        if commentQuery is not None:
            db.session.closed()
            return True
    db.session.close()
    return False