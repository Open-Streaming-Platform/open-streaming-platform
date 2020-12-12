from flask import Blueprint, request, url_for, render_template, redirect, current_app, send_from_directory, abort, flash

root_bp = Blueprint('root', __name__)

@root_bp.route('/playbackAuth', methods=['POST'])
def playback_auth_handler():
    stream = request.form['name']
    clientIP = request.form['addr']

    return 'OK'