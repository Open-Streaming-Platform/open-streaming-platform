from flask_security import current_user

from classes import upvotes


def get_Video_Upvotes(videoID: int) -> int:
    return upvotes.videoUpvotes.query.filter_by(videoID=videoID).count()


def get_Stream_Upvotes(videoID: int) -> int:
    return upvotes.streamUpvotes.query.filter_by(streamID=videoID).count()


def get_Clip_Upvotes(videoID: int) -> int:
    return upvotes.clipUpvotes.query.filter_by(clipID=videoID).count()


def check_isCommentUpvoted(commentID: int) -> bool:
    if current_user.is_authenticated:
        commentQuery = upvotes.commentUpvotes.query.filter_by(
            commentID=int(commentID), userID=current_user.id
        ).first()
        if commentQuery is not None:
            return True
    return False
