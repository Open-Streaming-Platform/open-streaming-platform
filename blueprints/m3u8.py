from functions import cachedDbCalls
import jinja2

from flask import Blueprint

m3u8_bp = Blueprint("m3u8", __name__, url_prefix="/m3u8")


@m3u8_bp.route("/stream/index.m3u8")
def get_stream_index():
    sysSettings = cachedDbCalls.getSystemSettings()
    streams = cachedDbCalls.getAllStreams()
    templateLoader = jinja2.FileSystemLoader(searchpath="./templates/other")
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("streamIndex.m3u8")
    outputM3u8 = template.render(sysSettings=sysSettings, streams=streams)
    return outputM3u8


@m3u8_bp.route("/video/index.m3u8")
def get_all_video_index():
    sysSettings = cachedDbCalls.getSystemSettings()
    videoQuery = cachedDbCalls.getAllVideo()
    templateLoader = jinja2.FileSystemLoader(searchpath="./templates/other")
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("videos.m3u8")
    outputM3u8 = template.render(sysSettings=sysSettings, videos=videoQuery)
    return outputM3u8
