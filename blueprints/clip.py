from flask import Blueprint, request, url_for, render_template, redirect, flash
from flask_security import current_user, login_required
from sqlalchemy.sql.expression import func

from classes.shared import db
from classes import settings
from classes import RecordedVideo
from classes import subscriptions
from classes import topics

from functions import themes
from functions import videoFunc
from functions import securityFunc

from globals import globalvars

clip_bp = Blueprint('clip', __name__, url_prefix='/clip')

@clip_bp.route('/<clipID>')
def view_clip_page(clipID):
    sysSettings = cachedDbCalls.getSystemSettings()
    videos_root = globalvars.videoRoot + 'videos/'

    clipQuery = RecordedVideo.Clips.query.filter_by(id=int(clipID)).first()

    if clipQuery is not None:

        recordedVid = RecordedVideo.RecordedVideo.query.filter_by(id=clipQuery.recordedVideo.id).first()

        if clipQuery.published is False:
            if current_user.is_authenticated:
                if current_user != clipQuery.recordedVideo.owningUser and current_user.has_role('Admin') is False:
                    flash("No Such Video at URL", "error")
                    return redirect(url_for("root.main_page"))
            else:
                flash("No Such Video at URL", "error")
                return redirect(url_for("root.main_page"))

        if recordedVid.channel.protected and sysSettings.protectionEnabled:
            if not securityFunc.check_isValidChannelViewer(clipQuery.recordedVideo.channel.id):
                return render_template(themes.checkOverride('channelProtectionAuth.html'))

        if recordedVid is not None:
            clipQuery.views = clipQuery.views + 1
            clipQuery.recordedVideo.channel.views = clipQuery.recordedVideo.channel.views + 1

            if recordedVid.length is None:
                fullVidPath = videos_root + recordedVid.videoLocation
                duration = videoFunc.getVidLength(fullVidPath)
                recordedVid.length = duration
            db.session.commit()

            topicList = topics.topics.query.all()

            streamURL = '/videos/' + clipQuery.videoLocation

            isEmbedded = request.args.get("embedded")

            if isEmbedded is None or isEmbedded == "False":

                randomClips = RecordedVideo.Clips.query.filter(RecordedVideo.Clips.id != clipQuery.id).filter(RecordedVideo.Clips.published == True).order_by(func.random()).limit(12)

                subState = False
                if current_user.is_authenticated:
                    chanSubQuery = subscriptions.channelSubs.query.filter_by(channelID=recordedVid.channel.id, userID=current_user.id).first()
                    if chanSubQuery is not None:
                        subState = True

                return render_template(themes.checkOverride('clipplayer.html'), video=recordedVid, streamURL=streamURL, topics=topicList, randomClips=randomClips, subState=subState, clip=clipQuery)
            #else:
            #    isAutoPlay = request.args.get("autoplay")
            #    if isAutoPlay == None:
            #        isAutoPlay = False
            #    elif isAutoPlay.lower() == 'true':
            #        isAutoPlay = True
            #    else:
            #        isAutoPlay = False
            #    return render_template(themes.checkOverride('vidplayer_embed.html'), video=recordedVid, streamURL=streamURL, topics=topicList, isAutoPlay=isAutoPlay, startTime=startTime)
    else:
        flash("No Such Clip at URL","error")
        return redirect(url_for("root.main_page"))

@clip_bp.route('/<clipID>/delete')
@login_required
def delete_clip_page(clipID):

    result = videoFunc.deleteClip(int(clipID))

    if result is True:
        flash("Clip deleted")
        return redirect(url_for('root.main_page'))
    else:
        flash("Error Deleting Clip")
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