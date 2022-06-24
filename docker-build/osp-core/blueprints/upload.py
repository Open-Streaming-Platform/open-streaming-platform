import os
import datetime
import subprocess
import shutil

from flask import (
    Blueprint,
    request,
    url_for,
    render_template,
    redirect,
    flash,
    current_app,
)
from flask_security import current_user, login_required, roles_required
from werkzeug.utils import secure_filename

from classes.shared import db
from classes import Channel

from functions import system
from functions import cachedDbCalls
from functions import videoFunc
from functions.scheduled_tasks import video_tasks

from globals import globalvars

upload_bp = Blueprint("upload", __name__, url_prefix="/upload")


@upload_bp.route("/video-files", methods=["GET", "POST"])
@login_required
@roles_required("Uploader")
def upload():
    videos_root = globalvars.videoRoot + "videos/"

    sysSettings = cachedDbCalls.getSystemSettings()
    if not sysSettings.allowUploads:
        db.session.close()
        return "Video Uploads Disabled", 501
    if request.files["file"]:

        if not os.path.exists(videos_root + "temp"):
            os.makedirs(videos_root + "temp")

        file = request.files["file"]

        if request.form["ospfilename"] != "":
            ospfilename = request.form["ospfilename"]
        else:
            return "Ooops.", 500

        if system.videoupload_allowedExt(
            file.filename, current_app.config["VIDEO_UPLOAD_EXTENSIONS"]
        ):
            save_path = os.path.join(
                current_app.config["VIDEO_UPLOAD_TEMPFOLDER"],
                secure_filename(ospfilename),
            )
            current_chunk = int(request.form["dzchunkindex"])
        else:
            system.newLog(
                4,
                "File Upload Failed - File Type not Allowed - Username:"
                + current_user.username,
            )
            return "Filetype not allowed", 403

        if current_chunk > 4500:
            open(save_path, "w").close()
            return "File is getting too large.", 403

        if os.path.exists(save_path) and current_chunk == 0:
            open(save_path, "w").close()

        try:
            with open(save_path, "ab") as f:
                f.seek(int(request.form["dzchunkbyteoffset"]))
                f.write(file.stream.read())
        except OSError:
            system.newLog(
                4, "File Upload Failed - OSError - Username:" + current_user.username
            )
            return "Ooops.", 500

        total_chunks = int(request.form["dztotalchunkcount"])

        if current_chunk + 1 == total_chunks:
            if os.path.getsize(save_path) != int(request.form["dztotalfilesize"]):
                return "Size mismatch", 500

        return "success", 200
    else:
        return "I don't understand", 501


@upload_bp.route("/video-details", methods=["POST"])
@login_required
@roles_required("Uploader")
def upload_vid():
    sysSettings = cachedDbCalls.getSystemSettings()
    if not sysSettings.allowUploads:
        db.session.close()
        flash("Video Upload Disabled", "error")
        return redirect(url_for("root.main_page"))

    channel = int(request.form["uploadToChannelID"])
    topic = int(request.form["uploadTopic"])
    thumbnailFilename = request.form["thumbnailFilename"]
    videoFilename = request.form["videoFilename"]
    videoTitle = request.form["videoTitle"]
    videoDescription = request.form["videoDescription"]

    # ChannelQuery = Channel.Channel.query.filter_by(id=channel).first()
    ChannelQuery = cachedDbCalls.getChannel(channel)

    if ChannelQuery.owningUser != current_user.id:
        flash("You are not allowed to upload to this channel!")
        db.session.close()
        return redirect(url_for("root.main_page"))

    else:
        results = video_tasks.process_video_upload.delay(
            videoFilename,
            thumbnailFilename,
            topic,
            videoTitle,
            videoDescription,
            ChannelQuery.id,
        )

    db.session.commit()
    db.session.close()
    flash("Video upload queued for processing", "success")
    return redirect(url_for("root.main_page"))
