from threading import Thread
from functools import wraps
import subprocess
import os
import datetime
import smtplib
from flask import flash
from html.parser import HTMLParser
import ipaddress
import json

from globals import globalvars

from classes.shared import db
from classes import settings
from classes import logs
from classes import RecordedVideo

def asynch(func):

    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target = func, args = args, kwargs = kwargs)
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
        return ''.join(self.fed)

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
            ipaddress.ip_address(systemAddress.split(':')[0])
            return systemAddress.split(':')[0]
        except ValueError:
            return systemAddress

def table2Dict(table):
    exportedTableList = table.query.all()
    dataList = []
    for tbl in exportedTableList:
        dataList.append(dict((column.name, str(getattr(tbl, column.name))) for column in tbl.__table__.columns))
    return dataList

def sendTestEmail(smtpServer, smtpPort, smtpTLS, smtpSSL, smtpUsername, smtpPassword, smtpSender, smtpReceiver):
    sslContext = None
    if smtpSSL is True:
        import ssl
        sslContext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)

    server = smtplib.SMTP(smtpServer, int(smtpPort))
    try:
        if smtpTLS or smtpSSL:
            server.ehlo()
            if smtpSSL:
                server.starttls(context=sslContext)
            else:
                server.starttls()
            server.ehlo()
        if smtpUsername and smtpPassword:
            server.login(smtpUsername, smtpPassword)
        msg = "Test Email - Your Instance of OSP has been successfully configured!"
        server.sendmail(smtpSender, smtpReceiver, msg)
    except Exception as e:
        print(e)
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
                f.write(str(edge.loadPct) + "% " + edge.address + ":" + str(edge.port) +";\n" )
    else:
        f.write("100% 127.0.0.1;\n")
    f.write("}")
    f.close()
    return True

def systemFixes(app):

    print({"level": "info", "message": "Checking for 0.7.x Clips"})
    # Fix for Beta 6 Switch from Fake Clips to real clips
    clipQuery = RecordedVideo.Clips.query.filter_by(videoLocation=None).all()
    videos_root = globalvars.videoRoot + 'videos/'
    for clip in clipQuery:
        originalVideo = videos_root + clip.recordedVideo.videoLocation
        clipVideoLocation = clip.recordedVideo.channel.channelLoc + '/clips/' + 'clip-' + str(clip.id) + ".mp4"
        fullvideoLocation = videos_root + clipVideoLocation
        clip.videoLocation = clipVideoLocation
        clipVideo = subprocess.run(['ffmpeg', '-ss', str(clip.startTime), '-i', originalVideo, '-c', 'copy', '-t', str(clip.length), '-avoid_negative_ts', '1', fullvideoLocation])
        db.session.commmit()

    # Create the stream-thumb directory if it does not exist
    if not os.path.isdir(app.config['WEB_ROOT'] + "stream-thumb"):
        try:
            os.mkdir(app.config['WEB_ROOT'] + "stream-thumb")
        except OSError:
            flash("Unable to create <web-root>/stream-thumb", "error")

    return True

def initializeThemes():
    sysSettings = settings.settings.query.first()

    print({"level": "info", "message": "Importing Theme Data into Global Cache"})
    # Import Theme Data into Theme Dictionary
    with open('templates/themes/' + sysSettings.systemTheme + '/theme.json') as f:
        globalvars.themeData = json.load(f)
    return True

def checkOSPEdgeConf():
    sysSettings = settings.settings.query.first()

    print({"level": "info", "message": "Rebuilding OSP Edge Conf File"})
    # Initialize the OSP Edge Configuration - Mostly for Docker
    if sysSettings.buildEdgeOnRestart is True:
        try:
            rebuildOSPEdgeConf()
        except:
            print("Error Rebuilding Edge Config")
            return False
    else:
        print({"level": "info", "message": "Skipping Rebuilding '/opt/osp/conf/osp-edge.conf' per System Setting"})
    return True