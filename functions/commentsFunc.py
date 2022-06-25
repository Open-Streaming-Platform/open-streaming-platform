from classes import comments


def get_Video_Comments(videoID):
    videoCommentsQuery = comments.videoComments.query.filter_by(videoID=videoID).count()
    result = videoCommentsQuery
    return result
