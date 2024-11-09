from classes import comments


def get_Video_Comments(videoID: str) -> int:
    return comments.videoComments.query.filter_by(videoID=videoID).count()
