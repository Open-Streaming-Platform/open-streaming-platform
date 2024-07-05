import os
import datetime
import uuid
import re
import bleach

from flask import (
    request,
    flash,
    render_template,
    redirect,
    url_for,
    Blueprint,
    session,
)
from flask_security import (
    current_user,
    login_required,
    logout_user,
)
from flask_security.utils import hash_password

from classes.shared import db, email
from classes import Channel
from classes import settings
from classes import banList
from classes import Sec
from classes import invites
from classes import subscriptions

from functions import system
from functions import themes
from functions import securityFunc

from globals import globalvars

from app import photos


user_settings_bp = Blueprint("user_settings", __name__, url_prefix="/user")


@user_settings_bp.route("/", methods=["POST", "GET"])
@login_required
def user_page():
    if request.method == "GET":
        # Checks Total Used Space
        userChannels = (
            Channel.Channel.query.filter_by(owningUser=current_user.id)
            .with_entities(Channel.Channel.channelLoc, Channel.Channel.channelName)
            .all()
        )
        socialNetworks = (
            Sec.UserSocial.query.filter_by(userID=current_user.id)
            .with_entities(
                Sec.UserSocial.id, Sec.UserSocial.socialType, Sec.UserSocial.url
            )
            .all()
        )

        totalSpaceUsed = 0
        channelUsage = []
        for chan in userChannels:
            try:
                videos_root = globalvars.videoRoot + "videos/"
                channelLocation = videos_root + chan.channelLoc

                total_size = 0
                for dirpath, dirnames, filenames in os.walk(channelLocation):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        total_size += os.path.getsize(fp)
            except FileNotFoundError:
                total_size = 0
            channelUsage.append({"name": chan.channelName, "usage": total_size})
            totalSpaceUsed = totalSpaceUsed + total_size

        return render_template(
            themes.checkOverride("userSettings.html"),
            totalSpaceUsed=totalSpaceUsed,
            channelUsage=channelUsage,
            socialNetworkList=socialNetworks,
        )

    elif request.method == "POST":

        biography = request.form["biography"]
        current_user.biography = bleach.clean(biography)

        if "emailVideo" in request.form:
            current_user.emailVideo = True
        else:
            current_user.emailVideo = False
        if "emailStream" in request.form:
            current_user.emailStream = True
        else:
            current_user.emailStream = False
        if "emailMessage" in request.form:
            current_user.emailMessage = True
        else:
            current_user.emailMessage = False

        if current_user.authType == 0:
            password1 = request.form["password1"]
            password2 = request.form["password2"]
            if password1 != "":
                if password1 == password2:
                    newPassword = hash_password(password1)
                    current_user.password = newPassword
                    system.newLog(
                        1, "User Password Changed - Username:" + current_user.username
                    )
                    flash("Password Changed")
                else:
                    flash("Passwords Don't Match!")

        userName = request.form["userName"].strip()
        if userName == '':
            flash("New username cannot be empty!", "error")
            return redirect(url_for(".user_page"))
        if len(userName) > 32:
            flash("New username is too long!", "error")
            return redirect(url_for(".user_page"))

        userName = bleach.clean(system.strip_html(userName))
        if userName == '':
            flash("New username would be empty after sanitization!", "error")
            return redirect(url_for(".user_page"))

        bannedWordQuery = banList.chatBannedWords.query.all()
        for bannedWord in bannedWordQuery:
            bannedWordRegex = bannedWord.word
            if bannedWordRegex == '':
                continue
            
            if re.search(bannedWordRegex, userName, flags=re.IGNORECASE) is not None:
                flash(f"New username has a banned word ({bannedWord.word})!", "error")
                return redirect(url_for(".user_page"))

        existingUsernameQuery = Sec.User.query.filter_by(username=userName).first()
        if existingUsernameQuery is not None:
            if existingUsernameQuery.id != current_user.id:
                flash(f"Another user has the name '{userName}'.", "error")
                return redirect(url_for(".user_page"))
        current_user.username = userName

        emailAddress = request.form["emailAddress"]
        existingEmailQuery = Sec.User.query.filter_by(email=emailAddress).first()
        if existingEmailQuery is not None:
            if existingEmailQuery.id != current_user.id:
                # TODO Add Option to Merge Existing Account
                flash("An User Account exists with the same email address", "error")
                return redirect(url_for(".user_page"))
        current_user.email = emailAddress

        if "photo" in request.files:
            file = request.files["photo"]
            if file.filename != "":
                oldImage = None

                if current_user.pictureLocation is not None:
                    oldImage = current_user.pictureLocation

                filename = photos.save(
                    request.files["photo"], name=str(uuid.uuid4()) + "."
                )
                current_user.pictureLocation = filename

                if oldImage is not None:
                    try:
                        os.remove(oldImage)
                    except OSError:
                        pass

        system.newLog(1, "User Info Updated - Username:" + current_user.username)
        db.session.commit()
    flash("User Settings Updated", "success")
    return redirect(url_for(".user_page"))


@user_settings_bp.route("/subscriptions")
@login_required
def subscription_page():
    channelSubList = (
        subscriptions.channelSubs.query.filter_by(userID=current_user.id)
        .with_entities(
            subscriptions.channelSubs.id, subscriptions.channelSubs.channelID
        )
        .all()
    )

    return render_template(
        themes.checkOverride("subscriptions.html"), channelSubList=channelSubList
    )


@user_settings_bp.route("/deleteSelf", methods=["POST"])
@login_required
def user_delete_own_account():
    """
    Endpoint to allow user to delete own account and all associated data.
    Not to be called directly without confirmation UI
    """
    userConfirmation = request.form["usernameDeleteConfirmation"]

    if userConfirmation == current_user.username:
        securityFunc.flag_delete_user(current_user.id)
        flash("Account and Associated Data Scheduled for Deletion", "error")
        logout_user()
    else:
        flash("Invalid Deletion Request", "error")
    return redirect(url_for("root.main_page"))


@user_settings_bp.route("/addInviteCode")
def user_addInviteCode():
    if "inviteCode" in request.args:
        inviteCode = request.args.get("inviteCode")
        inviteCodeQuery = invites.inviteCode.query.filter_by(code=inviteCode).first()
        if inviteCodeQuery is not None:
            if inviteCodeQuery.isValid():
                # Add Check if User is Authenticated to Add Code
                if current_user.is_authenticated:
                    existingInviteQuery = invites.invitedViewer.query.filter_by(
                        inviteCode=inviteCodeQuery.id, userID=current_user.id
                    ).first()
                    if existingInviteQuery is None:
                        if inviteCodeQuery.expiration is not None:
                            remainingDays = (
                                inviteCodeQuery.expiration - datetime.datetime.utcnow()
                            ).days
                        else:
                            remainingDays = 0
                        newInvitedUser = invites.invitedViewer(
                            current_user.id,
                            inviteCodeQuery.channelID,
                            remainingDays,
                            inviteCode=inviteCodeQuery.id,
                        )
                        inviteCodeQuery.uses = inviteCodeQuery.uses + 1
                        db.session.add(newInvitedUser)
                        db.session.commit()
                        system.newLog(
                            3,
                            "User Added Invite Code to Account - Username:"
                            + current_user.username
                            + " Channel ID #"
                            + str(inviteCodeQuery.channelID),
                        )
                        flash("Added Invite Code to Channel", "success")
                        if "redirectURL" in request.args:
                            return redirect(request.args.get("redirectURL"))
                    else:
                        flash("Invite Code Already Applied", "error")
                else:
                    if "inviteCodes" not in session:
                        session["inviteCodes"] = []
                    if inviteCodeQuery.code not in session["inviteCodes"]:
                        session["inviteCodes"].append(inviteCodeQuery.code)
                        inviteCodeQuery.uses = inviteCodeQuery.uses + 1
                        system.newLog(
                            3,
                            "User Added Invite Code to Account - Username:"
                            + "Guest"
                            + "-"
                            + session["guestUUID"]
                            + " Channel ID #"
                            + str(inviteCodeQuery.channelID),
                        )
                    else:
                        flash("Invite Code Already Applied", "error")
            else:
                if current_user.is_authenticated:
                    system.newLog(
                        3,
                        "User Attempted to add Expired Invite Code to Account - Username:"
                        + current_user.username
                        + " Channel ID #"
                        + str(inviteCodeQuery.channelID),
                    )
                else:
                    system.newLog(
                        3,
                        "User Attempted to add Expired Invite Code to Account - Username:"
                        + "Guest"
                        + "-"
                        + session["guestUUID"]
                        + " Channel ID #"
                        + str(inviteCodeQuery.channelID),
                    )
                flash("Invite Code Expired", "error")
        else:
            flash("Invalid Invite Code", "error")
    return redirect(url_for("root.main_page"))
