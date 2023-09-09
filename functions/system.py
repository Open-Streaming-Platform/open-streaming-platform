from threading import Thread
from functools import wraps
import subprocess
import os
import datetime
import smtplib
from flask import flash, current_app
from html.parser import HTMLParser
import ipaddress
import json
import secrets
import logging
import time
import shutil
from pathlib import Path

from globals import globalvars

from classes.shared import db
from classes import settings
from classes import logs
from classes import RecordedVideo
from classes import Sec

from functions import cachedDbCalls, templateFilters

from classes.shared import celery

log = logging.getLogger("app.functions.system")




def asynch(func):
    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target=func, args=args, kwargs=kwargs)
        func_hl.start()
        return func_hl

    return async_func


def check_existing_settings():
    settingsQuery = settings.settings.query.all()
    if settingsQuery != []:
        db.session.close()
        return True
    else:
        db.session.close()
        return False


# Class Required for HTML Stripping in strip_html
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return "".join(self.fed)


def strip_html(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def videoupload_allowedExt(filename, allowedExtensions):
    if not "." in filename:
        return False
    ext = filename.rsplit(".", 1)[1]
    if ext.upper() in allowedExtensions:
        return True
    else:
        return False


def formatSiteAddress(systemAddress):
    try:
        ipaddress.ip_address(systemAddress)
        return systemAddress
    except ValueError:
        try:
            ipaddress.ip_address(systemAddress.split(":")[0])
            return systemAddress.split(":")[0]
        except ValueError:
            return systemAddress


def table2Dict(table):
    exportedTableList = table.query.all()
    dataList = []
    for tbl in exportedTableList:
        dataList.append(
            dict(
                (column.name, str(getattr(tbl, column.name)))
                for column in tbl.__table__.columns
            )
        )
    return dataList


def parseTags(tagString):
    tagString = tagString.split(",")
    return tagString


def sendTestEmail(
    smtpServer,
    smtpPort,
    smtpTLS,
    smtpSSL,
    smtpUsername,
    smtpPassword,
    smtpSender,
    smtpReceiver,
):
    try:
        server = smtplib.SMTP(smtpServer, int(smtpPort))
        if smtpSSL is True:
            server = smtplib.SMTP_SSL(smtpServer, int(smtpPort))
        if smtpTLS is True:
            server.starttls()
        server.ehlo()
        if smtpUsername and smtpPassword:
            server.login(smtpUsername, smtpPassword)
        msg = "Test Email - Your Instance of OSP has been successfully configured!"
        server.sendmail(smtpSender, smtpReceiver, msg)
    except Exception as e:
        current_app.logger.error(e)
        newLog(1, "Test Email Failed for " + str(smtpServer) + "Reason:" + str(e))
        return False
    server.quit()
    newLog(1, "Test Email Successful for " + str(smtpServer))
    return True


def newLog(logType, message):
    newLogItem = logs.logs(datetime.datetime.utcnow(), str(message), logType)
    db.session.add(newLogItem)
    db.session.commit()
    return True


def rebuildOSPEdgeConf():
    f = open("/opt/osp/conf/osp-edge.conf", "w")
    ospEdgeQuery = settings.edgeStreamer.query.filter_by(active=True).all()
    f.write('split_clients "${remote_addr}AAA" $ospedge_node {\n')
    if ospEdgeQuery != []:
        for edge in ospEdgeQuery:
            if edge.port == 80 or edge.port == 443:
                f.write(str(edge.loadPct) + "% " + edge.address + ";\n")
            else:
                f.write(
                    str(edge.loadPct)
                    + "% "
                    + edge.address
                    + ":"
                    + str(edge.port)
                    + ";\n"
                )
    else:
        f.write("100% 127.0.0.1;\n")
    f.write("}")
    f.close()
    return True


def systemFixes(app):

    log.info({"level": "info", "message": "Checking for 0.7.x Clips"})
    # Fix for Beta 6 Switch from Fake Clips to real clips
    clipQuery = RecordedVideo.Clips.query.filter_by(videoLocation=None).all()
    videos_root = globalvars.videoRoot + "videos/"
    for clip in clipQuery:
        videoQuery = cachedDbCalls.getVideo(clip.parentVideo)
        channelQuery = cachedDbCalls.getChannel(videoQuery.channelID)
        originalVideo = videos_root + videoQuery
        clipVideoLocation = (
            channelQuery.channelLoc
            + "/clips/"
            + "clip-"
            + str(clip.id)
            + ".mp4"
        )
        fullvideoLocation = videos_root + clipVideoLocation
        clip.videoLocation = clipVideoLocation
        clipVideo = subprocess.run(
            [
                "ffmpeg",
                "-ss",
                str(clip.startTime),
                "-i",
                originalVideo,
                "-c",
                "copy",
                "-t",
                str(clip.length),
                "-avoid_negative_ts",
                "1",
                fullvideoLocation,
            ]
        )
        db.session.commmit()

    log.info({"level": "info", "message": "Checking Stickers Directory"})
    # Create the Stickers directory if it does not exist
    if not os.path.isdir(app.config["WEB_ROOT"] + "/images/stickers"):
        try:
            os.mkdir(app.config["WEB_ROOT"] + "/images/stickers")
        except OSError:
            flash("Unable to create <web-root>/images/stickers", "error")

    log.info({"level": "info", "message": "Checking stream-thumb directory"})
    # Create the stream-thumb directory if it does not exist
    if not os.path.isdir(app.config["WEB_ROOT"] + "stream-thumb"):
        try:
            os.mkdir(app.config["WEB_ROOT"] + "stream-thumb")
        except OSError:
            flash("Unable to create <web-root>/stream-thumb", "error")

    log.info(
        {
            "level": "info",
            "message": "Checking for fs_uniquifier for Flask-Security-Too",
        }
    )
    # Check fs_uniquifier
    userQuery = Sec.User.query.filter_by(fs_uniquifier=None).all()
    for user in userQuery:
        user.fs_uniquifier = str(secrets.token_hex(nbytes=16))
        db.session.commit()

    log.info({"level": "info", "message": "Checking Pre 0.9.x Favicon Location"})
    path = Path(globalvars.videoRoot + "/images/favicon.ico")
    if not path.is_file():
        transferFiles = [
            "android-chrome-192x192.png",
            "android-chrome-512x512.png",
            "apple-touch-icon.png",
            "favicon.ico",
            "favicon-16x16.png",
            "favicon-32x32.png",
        ]
        for file in transferFiles:
            shutil.copy(
                "/opt/osp/static/" + file,
                globalvars.videoRoot + "/images/",
                follow_symlinks=True,
            )

    return True


def initializeThemes():
    sysSettings = cachedDbCalls.getSystemSettings()

    log.info({"level": "info", "message": "Importing Theme Data into Global Cache"})
    # Import Theme Data into Theme Dictionary
    with open("templates/themes/" + sysSettings.systemTheme + "/theme.json") as f:
        globalvars.themeData = json.load(f)
    return True


def checkOSPEdgeConf():
    sysSettings = cachedDbCalls.getSystemSettings()

    log.info({"level": "info", "message": "Rebuilding OSP Edge Conf File"})
    # Initialize the OSP Edge Configuration - Mostly for Docker
    if sysSettings.buildEdgeOnRestart is True:
        try:
            rebuildOSPEdgeConf()
        except:
            log.error("Error Rebuilding Edge Config")
            return False
    else:
        log.info(
            {
                "level": "info",
                "message": "Skipping Rebuilding '/opt/osp/conf/osp-edge.conf' per System Setting",
            }
        )
    return True


@celery.task()
def testCelery():
    print("testing celery")
    time.sleep(60)
    return True
