from flask import Blueprint, request, url_for, render_template, redirect, flash
from flask_security import current_user, login_required
from sqlalchemy.sql.expression import func

from classes.shared import db
from classes import settings
from classes import RecordedVideo
from classes import subscriptions
from classes import topics
from classes import Channel

from functions import themes
from functions import videoFunc
from functions import securityFunc
from functions import cachedDbCalls
from functions.scheduled_tasks import video_tasks

from globals import globalvars

clip_bp = Blueprint('clip', __name__, url_prefix='/clip')

@clip_bp.route('/<clipID>')
def view_clip_page(clipID):
    sysSettings = cachedDbCalls.getSystemSettings()
    videos_root = globalvars.videoRoot + 'videos/'

    clipQuery = RecordedVideo.Clips.query.filter_by(id=int(clipID)).first()

    if clipQuery is not None:

        recordedVid = cachedDbCalls.getVideo(clipQuery.recordedVideo.id)

        associatedChannel = cachedDbCalls.getChannel(recordedVid.channelID)

        if clipQuery.published is False:
            if current_user.is_authenticated:
                if current_user != recordedVid.owningUser and current_user.has_role('Admin') is False:
                    flash("No Such Video at URL", "error")
                    return redirect(url_for("root.main_page"))
            else:
                flash("No Such Video at URL", "error")
                return redirect(url_for("root.main_page"))

        if associatedChannel.private:
            if current_user.is_authenticated:
                if current_user.id != associatedChannel.owningUser and current_user.has_role('Admin') is False:
                    flash("No Such Video at URL", "error")
                    return redirect(url_for("root.main_page"))
            else:
                flash("No Such Video at URL", "error")
                return redirect(url_for("root.main_page"))

        if associatedChannel.protected and sysSettings.protectionEnabled:
            if not securityFunc.check_isValidChannelViewer(associatedChannel.id):
                return render_template(themes.checkOverride('channelProtectionAuth.html'))

        if recordedVid is not None:
            clipQuery.views = clipQuery.views + 1
            Channel.Channel.query.filter_by(id=associatedChannel.id).update(dict(views=associatedChannel.views + 1))

            if recordedVid.length is None:
                fullVidPath = videos_root + recordedVid.videoLocation
                duration = videoFunc.getVidLength(fullVidPath)
                recordedVid.length = duration
            db.session.commit()

            topicList = cachedDbCalls.getAllTopics()

            streamURL = '/videos/' + clipQuery.videoLocation

            isEmbedded = request.args.get("embedded")

            if isEmbedded is None or isEmbedded == "False":

                randomClips = RecordedVideo.Clips.query.filter(RecordedVideo.Clips.id != clipQuery.id).filter(RecordedVideo.Clips.published == True).order_by(func.random()).limit(4)

                subState = False
                if current_user.is_authenticated:
                    chanSubQuery = subscriptions.channelSubs.query.filter_by(channelID=recordedVid.channelID, userID=current_user.id).first()
                    if chanSubQuery is not None:
                        subState = True

                return render_template(themes.checkOverride('clipplayer.html'), video=recordedVid, streamURL=streamURL, topics=topicList, randomClips=randomClips, subState=subState, clip=clipQuery)
            else:
                isAutoPlay = request.args.get("autoplay")
                if isAutoPlay == None:
                    isAutoPlay = False
                elif isAutoPlay.lower() == 'true':
                    isAutoPlay = True
                else:
                    isAutoPlay = False
                return render_template(themes.checkOverride('vidplayer_embed.html'), video=clipQuery, streamURL=streamURL, topics=topicList, isAutoPlay=isAutoPlay)
    else:
        flash("No Such Clip at URL","error")
        return redirect(url_for("root.main_page"))

@clip_bp.route('/<clipID>/delete')
@login_required
def delete_clip_page(clipID):

    clipQuery = RecordedVideo.Clips.query.filter_by(id=clipID).first()
    if clipQuery.recordedVideo.owningUser == current_user.id or current_user.has_role('Admin'):
        result = video_tasks.delete_video_clip.delay(int(clipID))
        flash("Clip scheduled for deletion", "success")
        return redirect(url_for('root.main_page'))
    else:
        flash("Error Deleting Clip", "error")
        return redirect(url_for('.view_clip_page', clipID=clipID))

@clip_bp.route('/<clipID>/change', methods=['POST'])
@login_required
def clip_change_page(clipID):

    result = videoFunc.changeClipMetadata(int(clipID), request.form['newVidName'], request.form['description'])

    if result is True:
        flash("Updated Clip Metadata","success")
        return redirect(url_for('.view_clip_page', clipID=clipID))

    else:
        flash("Error Changing Clip Metadata", "error")
        return redirect(url_for("root.main_page"))