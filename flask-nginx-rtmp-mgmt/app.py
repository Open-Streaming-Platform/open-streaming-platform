from flask import Flask, redirect, request, abort, render_template, url_for, flash, sessionfrom flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, login_required, url_for_security, current_user, roles_requiredfrom flask_security.forms import RegisterForm, LoginForm, StringField, Requiredfrom flask_security.signals import user_registeredfrom flask_security import utilsfrom flask_sqlalchemy import SQLAlchemyfrom flask_socketio import SocketIO, emit, send, join_room, leave_room, roomsfrom flask_uploads import UploadSet, configure_uploads, IMAGES, UploadNotAllowed, patch_request_classimport uuidimport psutilimport shutilimport osimport loggingimport datetimeimport configapp = Flask(__name__)app.config['SQLALCHEMY_DATABASE_URI'] = config.dbLocationapp.config['SECRET_KEY'] = config.secretKeyapp.config['SECURITY_PASSWORD_HASH'] = "pbkdf2_sha512"app.config['SECURITY_PASSWORD_SALT'] = config.passwordSaltapp.config['SECURITY_REGISTERABLE'] = Trueapp.config['SECURITY_RECOVERABLE'] = Trueapp.config['SECURITY_CHANGABLE'] = Trueapp.config['SECURITY_CONFIRMABLE'] = Falseapp.config['SECURITY_USER_IDENTITY_ATTRIBUTES'] = ['username']app.config['SECURITY_FLASH_MESSAGES'] = Trueapp.config['UPLOADED_PHOTOS_DEST'] = '/var/www/images'app.config['UPLOADED_DEFAULT_DEST'] = '/var/www/images'logger = logging.getLogger('gunicorn.error').handlerssocketio = SocketIO(app,logger=True)appDBVersion = 0.1db = SQLAlchemy(app)sysSettings = Noneclass ExtendedRegisterForm(RegisterForm):    username = StringField('username', [Required()])roles_users = db.Table('roles_users',        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))class Role(db.Model, RoleMixin):    id = db.Column(db.Integer(), primary_key=True)    name = db.Column(db.String(80), unique=True)    description = db.Column(db.String(255))class User(db.Model, UserMixin):    id = db.Column(db.Integer, primary_key=True)    username = db.Column(db.String(255), unique=True)    email = db.Column(db.String(255), unique=True)    password = db.Column(db.String(255))    active = db.Column(db.Boolean())    confirmed_at = db.Column(db.DateTime())    roles = db.relationship('Role', secondary=roles_users,                            backref=db.backref('users', lazy='dynamic'))class Stream(db.Model):    __tablename__="Stream"    id = db.Column(db.Integer, primary_key=True)    linkedChannel = db.Column(db.Integer,db.ForeignKey('Channel.id'))    streamKey = db.Column(db.String)    streamName = db.Column(db.String)    topic = db.Column(db.Integer)    currentViewers = db.Column(db.Integer)    totalViewers = db.Column(db.Integer)    def __init__(self, streamKey, streamName, linkedChannel, topic):        self.streamKey = streamKey        self.streamName = streamName        self.linkedChannel = linkedChannel        self.currentViewers = 0        self.totalViewers = 0        self.topic = topic    def __repr__(self):        return '<id %r>' % self.id    def add_viewer(self):        self.currentViewers = self.currentViewers + 1        db.session.commit()    def remove_viewer(self):        self.currentViewers = self.currentViewers - 1        db.session.commit()class Channel(db.Model):    __tablename__="Channel"    id = db.Column(db.Integer, primary_key=True)    owningUser = db.Column(db.Integer, db.ForeignKey('user.id'))    streamKey = db.Column(db.String(255), unique=True)    channelName = db.Column(db.String(255))    channelLoc = db.Column(db.String(255), unique=True)    topic = db.Column(db.Integer)    views = db.Column(db.Integer)    record = db.Column(db.Boolean)    chatEnabled = db.Column(db.Boolean)    imageLocation = db.Column(db.String(255))    stream = db.relationship('Stream', backref='channel', lazy="joined")    recordedVideo = db.relationship('RecordedVideo', backref='channel', lazy="joined")    def __init__(self, owningUser, streamKey, channelName, topic, record, chatEnabled):        self.owningUser = owningUser        self.streamKey = streamKey        self.channelName = channelName        self.topic = topic        self.channelLoc = str(uuid.uuid4())        self.record = record        self.chatEnabled = chatEnabled        self.views = 0    def __repr__(self):        return '<id %r>' % self.idclass RecordedVideo(db.Model):    __tablename__="RecordedVideo"    id = db.Column(db.Integer,primary_key=True)    videoDate = db.Column(db.DateTime)    owningUser = db.Column(db.Integer,db.ForeignKey('user.id'))    channelName = db.Column(db.String(255))    channelID = db.Column(db.Integer,db.ForeignKey('Channel.id'))    topic = db.Column(db.Integer)    views = db.Column(db.Integer)    videoLocation = db.Column(db.String(255))    thumbnailLocation = db.Column(db.String(255))    pending = db.Column(db.Boolean)    def __init__(self,owningUser,channelID,channelName,topic,views,videoLocation):        self.videoDate = datetime.datetime.now()        self.owningUser=owningUser        self.channelID=channelID        self.channelName=channelName        self.topic=topic        self.views=views        self.videoLocation=videoLocation        self.pending = True    def __repr__(self):        return '<id %r>' % self.idclass topics(db.Model):    __table__name="topics"    id = db.Column(db.Integer, primary_key=True)    name = db.Column(db.String(255))    iconClass = db.Column(db.String(255))    def __init__(self, name, iconClass):        self.name = name        self.iconClass = iconClass    def __repr__(self):        return '<id %r>' % self.idclass settings(db.Model):    __table__name = "settings"    id = db.Column(db.Integer, primary_key=True)    siteName = db.Column(db.String(255))    siteAddress = db.Column(db.String(255))    smtpAddress = db.Column(db.String(255))    smtpPort = db.Column(db.Integer)    smtpTLS = db.Column(db.Boolean)    smtpUsername = db.Column(db.String(255))    smtpPassword = db.Column(db.String(255))    smtpSendAs = db.Column(db.String(255))    allowRegistration = db.Column(db.Boolean)    allowRecording = db.Column(db.Boolean)    background = db.Column(db.String(255))    def __init__(self, siteName, siteAddress, smtpAddress, smtpPort, smtpTLS, smtpUsername, smtpPassword, smtpSendAs, allowRegistration, allowRecording):        self.siteName = siteName        self.siteAddress = siteAddress        self.smtpAddress = smtpAddress        self.smtpPort = smtpPort        self.smtpTLS = smtpTLS        self.smtpUsername = smtpUsername        self.smtpPassword = smtpPassword        self.smtpSendAs = smtpSendAs        self.allowRegistration = allowRegistration        self.allowRecording = allowRecording        self.background = "Ash"    def __repr__(self):        return '<id %r>' % self.idclass dbVersion(db.Model):    __table__name = "dbVersion"    id = db.Column(db.Integer, primary_key=True)    version = db.Column(db.Float)    def __init__(self, version):        self.version = version    def __repr__(self):        return '<id %r>' % self.id# Setup Flask-Securityuser_datastore = SQLAlchemyUserDatastore(db, User, Role)security = Security(app, user_datastore, register_form=ExtendedRegisterForm)# Setup Flask-Uploadsphotos = UploadSet('photos', (IMAGES))configure_uploads(app, photos)patch_request_class(app)def init_db_values():    db.create_all()    dbVersionQuery = dbVersion.query.first()    if dbVersionQuery == None:        newDBVersion = dbVersion(appDBVersion)        db.session.add(newDBVersion)        db.session.commit()    user_datastore.find_or_create_role(name='Admin', description='Administrator')    user_datastore.find_or_create_role(name='User', description='User')    topicList = [("Static Webcam","&#xf03d;"),                 ("Gaming","&#xf11b;"),                 ("Meeting","&#xf0c0;"),                 ("News","&#xf1ea;"),                 ("Other","&#xf292;")]    for topic in topicList:        existingTopic = topics.query.filter_by(name=topic[0]).first()        if existingTopic is None:            newTopic = topics(topic[0], topic[1])            db.session.add(newTopic)    db.session.commit()    sysSettings = settings.query.first()    if sysSettings != None:        app.config['SECURITY_EMAIL_SENDER'] = sysSettings.smtpSendAs        app.config['MAIL_SERVER'] = sysSettings.smtpAddress        app.config['MAIL_PORT'] = sysSettings.smtpPort        app.config['MAIL_USE_SSL'] = sysSettings.smtpTLS        app.config['MAIL_USERNAME'] = sysSettings.smtpUsername        app.config['MAIL_PASSWORD'] = sysSettings.smtpPassword        app.config.update(SECURITY_REGISTERABLE=sysSettings.allowRegistration)def check_existing_users():    existingUserQuery = User.query.all()    if existingUserQuery == []:        return False    else:        return True@app.context_processordef inject_user_info():    return dict(user=current_user)@app.context_processordef inject_sysSettings():    sysSettings = settings.query.first()    return dict(sysSettings=sysSettings)@app.template_filter('normalize_uuid')def normalize_uuid(uuidstr):    return uuidstr.replace("-", "")@app.template_filter('normalize_date')def normalize_date(dateStr):    return str(dateStr)[:19]@app.template_filter('get_topicName')def get_topicName(topicID):    topicQuery = topics.query.filter_by(id=int(topicID)).first()    return topicQuery.name@app.template_filter('get_userName')def get_userName(userID):    userQuery = User.query.filter_by(id=int(userID)).first()    return userQuery.username@user_registered.connect_via(app)def user_registered_sighandler(app, user, confirm_token):    default_role = user_datastore.find_role("User")    user_datastore.add_role_to_user(user, default_role)    db.session.commit()@app.route('/')def main_page():    firstRunCheck = check_existing_users()    if firstRunCheck is False:        return render_template('firstrun.html')    else:        activeStreams = Stream.query.order_by(Stream.currentViewers).all()        return render_template('index.html',streamList=activeStreams)@app.route('/channels')def channels_page():    channelList = Channel.query.all()    return render_template('channels.html',channelList=channelList)@app.route('/channel/<chanID>/')def channel_view_page(chanID):    chanID = int(chanID)    channelData = Channel.query.filter_by(id=chanID).first()    openStreams = Stream.query.filter_by(linkedChannel=chanID).all()    recordedVids = RecordedVideo.query.filter_by(channelID=chanID, pending=False).all()    return render_template('channelView.html', channelData=channelData, openStreams=openStreams, recordedVids=recordedVids)@app.route('/view/<loc>/')def view_page(loc):    sysSettings = settings.query.first()    requestedChannel = Channel.query.filter_by(channelLoc=loc).first()    streamData = Stream.query.filter_by(streamKey=requestedChannel.streamKey).first()    if streamData is not None:        streamURL = ""        if streamData.channel.record is True:            streamURL = 'http://' + sysSettings.siteAddress + '/live-rec/' + streamData.channel.channelLoc + '/index.m3u8'        elif streamData.channel.record is False:            streamURL = 'http://' + sysSettings.siteAddress + '/live/' + streamData.channel.channelLoc + '/index.m3u8'        streamData.channel.views = streamData.channel.views + 1        streamData.totalViewers = streamData.totalViewers + 1        db.session.commit()        topicList = topics.query.all()        return render_template('player.html', stream=streamData, streamURL=streamURL, topics=topicList)    else:        return redirect(url_for("main_page"))@app.route('/view/<loc>/change', methods=['POST'])@login_requireddef view_change_page(loc):    requestedChannel = Channel.query.filter_by(channelLoc=loc, owningUser=current_user.id).first()    streamData = Stream.query.filter_by(streamKey=requestedChannel.streamKey).first()    newStreamName = request.form['newStreamName']    newStreamTopic = request.form['newStreamTopic']    if streamData is not None:        streamData.streamName = newStreamName        streamData.topic = newStreamTopic        db.session.commit()    return redirect(url_for('view_page', loc=loc))@app.route('/play/<videoID>')def view_vid_page(videoID):    sysSettings = settings.query.first()    recordedVid = RecordedVideo.query.filter_by(id=videoID).first()    recordedVid.views = recordedVid.views + 1    db.session.commit()    streamURL = 'http://' + sysSettings.siteAddress + '/videos/' + recordedVid.videoLocation    return render_template('vidplayer.html', video=recordedVid, streamURL=streamURL)@app.route('/play/<videoID>/delete')@login_requireddef delete_vid_page(videoID):    recordedVid = RecordedVideo.query.filter_by(id=videoID).first()    if current_user.id == recordedVid.owningUser:        filePath = '/var/www/videos/' + recordedVid.videoLocation        shutil.rmtree(filePath, ignore_errors=True)        db.session.delete(recordedVid)        db.session.commit()        return redirect(url_for('main_page'))@app.route('/settings/admin', methods=['POST','GET'])@login_required@roles_required('Admin')def admin_page():    if request.method == 'GET':        appDBVer = dbVersion.query.first().version        userList = User.query.all()        roleList = Role.query.all()        channelList = Channel.query.all()        return render_template('admin.html', appDBVer=appDBVer, userList=userList, roleList=roleList, channelList=channelList)    elif request.method =='POST':        sysSettings = settings.query.first()        serverName = request.form['serverName']        serverAddress = request.form['serverAddress']        smtpSendAs = request.form['smtpSendAs']        smtpAddress = request.form['smtpAddress']        smtpPort = request.form['smtpPort']        smtpUser = request.form['smtpUser']        smtpPassword = request.form['smtpPassword']        background = request.form['background']        recordSelect = False        registerSelect = False        smtpTLS = False        if 'recordSelect' in request.form:            recordSelect = True        if 'registerSelect' in request.form:            registerSelect = True        if 'smtpTLS' in request.form:            smtpTLS = True        sysSettings.siteName = serverName        sysSettings.siteAddress = serverAddress        sysSettings.smtpSendAs = smtpSendAs        sysSettings.smtpAddress = smtpAddress        sysSettings.smtpPort = smtpPort        sysSettings.smtpUsername = smtpUser        sysSettings.smtpPassword = smtpPassword        sysSettings.smtpTLS = smtpTLS        sysSettings.allowRecording = recordSelect        sysSettings.allowRegistration = registerSelect        sysSettings.background = background        db.session.commit()        sysSettings = settings.query.first()        app.config.update(SECURITY_EMAIL_SENDER=sysSettings.smtpSendAs)        app.config.update(MAIL_SERVER=sysSettings.smtpAddress)        app.config.update(MAIL_PORT=sysSettings.smtpPort)        app.config.update(MAIL_USE_SSL=sysSettings.smtpTLS)        app.config.update(MAIL_USERNAME=sysSettings.smtpUsername)        app.config.update(MAIL_PASSWORD=sysSettings.smtpPassword)        app.config.update(SECURITY_REGISTERABLE=sysSettings.allowRegistration)        return redirect(url_for('admin_page'))@app.route('/settings/channels', methods=['POST','GET'])@login_requireddef settings_channels_page():    sysSettings = settings.query.first()    if request.method == 'GET':        if request.args.get("action") is not None:            action = request.args.get("action")            streamKey = request.args.get("streamkey")            requestedChannel = Channel.query.filter_by(streamKey=streamKey).first()            if action == "delete":                if current_user.id == requestedChannel.id:                    db.session.delete(requestedChannel)                    db.session.commit()                    flash("Channel Deleted")                else:                    flash("Invalid Deletion Attempt","Error")    elif request.method == 'POST':        type = request.form['type']        channelName = request.form['channelName']        topic = request.form['channeltopic']        record = False        if 'recordSelect' in request.form and sysSettings.allowRecording is True:            record = True        chatEnabled = False        if 'chatSelect' in request.form:            chatEnabled = True        if type == 'new':            newUUID = str(uuid.uuid4())            newChannel = Channel(current_user.id, newUUID, channelName, topic, record, chatEnabled)            db.session.add(newChannel)            db.session.commit()        elif type == 'change':            streamKey = request.form['streamKey']            origStreamKey = request.form['origStreamKey']            requestedChannel = Channel.query.filter_by(streamKey=origStreamKey).first()            if current_user.id == requestedChannel.owningUser:                requestedChannel.channelName = channelName                requestedChannel.streamKey = streamKey                requestedChannel.topic = topic                requestedChannel.record = record                requestedChannel.chatEnabled = chatEnabled                if 'photo' in request.files:                    oldImage = None                    if requestedChannel.imageLocation != None:                        oldImage = requestedChannel.imageLocation                    filename = photos.save(request.files['photo'], name=str(uuid.uuid4()) + '.')                    requestedChannel.imageLocation = filename                    if oldImage != None:                        try:                            os.remove(oldImage)                        except OSError:                            pass                flash("Channel Edited")                db.session.commit()            else:                flash("Invalid Change Attempt","Error")            redirect(url_for('settings_channels_page'))    topicList = topics.query.all()    user_channels = Channel.query.filter_by(owningUser = current_user.id).all()    return render_template('user_channels.html', channels=user_channels, topics=topicList)@app.route('/settings/initialSetup', methods=['POST'])def initialSetup():    firstRunCheck = check_existing_users()    if firstRunCheck is False:        username = request.form['username']        email = request.form['email']        password1 = request.form['password1']        password2 = request.form['password2']        serverName = request.form['serverName']        serverAddress = request.form['serverAddress']        smtpSendAs = request.form['smtpSendAs']        smtpAddress = request.form['smtpAddress']        smtpPort = request.form['smtpPort']        smtpUser = request.form['smtpUser']        smtpPassword = request.form['smtpPassword']        recordSelect = False        registerSelect = False        smtpTLS = False        if 'recordSelect' in request.form:            recordSelect = True        if 'registerSelect' in request.form:            registerSelect = True        if 'smtpTLS' in request.form:            smtpTLS = True        if password1 == password2:            passwordhash = utils.hash_password(password1)            user_datastore.create_user(email=email, username=username, password=passwordhash)            db.session.commit()            user = User.query.filter_by(username=username).first()            user_datastore.add_role_to_user(user,'Admin')            serverSettings = settings(serverName, serverAddress, smtpAddress, smtpPort, smtpTLS, smtpUser, smtpPassword, smtpSendAs, registerSelect, recordSelect)            db.session.add(serverSettings)            db.session.commit()            sysSettings = settings.query.first()            if settings != None:                app.config.update(SECURITY_EMAIL_SENDER=sysSettings.smtpSendAs)                app.config.update(MAIL_SERVER=sysSettings.smtpAddress)                app.config.update(MAIL_PORT=sysSettings.smtpPort)                app.config.update(MAIL_USE_SSL=sysSettings.smtpTLS)                app.config.update(MAIL_USERNAME=sysSettings.smtpUsername)                app.config.update(MAIL_PASSWORD=sysSettings.smtpPassword)                app.config.update(SECURITY_REGISTERABLE=sysSettings.allowRegistration)        else:            flash('Passwords do not match')            return redirect(url_for('main_page'))    return redirect(url_for('main_page'))@app.route('/auth-key', methods=['POST'])def streamkey_check():    sysSettings = settings.query.first()    key = request.form['name']    ipaddress = request.form['addr']    channelRequest = Channel.query.filter_by(streamKey=key).first()    if channelRequest is not None:        returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Successful Key Auth', 'key':str(key), 'channelName': str(channelRequest.channelName), 'userName':str(channelRequest.owningUser), 'ipAddress': str(ipaddress)}        print(returnMessage)        newStream = Stream(key,str(channelRequest.channelName),int(channelRequest.id),channelRequest.topic)        db.session.add(newStream)        db.session.commit()        if channelRequest.record is False:            return redirect('rtmp://' + sysSettings.siteAddress + '/stream-data/' + channelRequest.channelLoc, code=302)        elif channelRequest.record is True:            userCheck = User.query.filter_by(id=channelRequest.owningUser).first()            newRecording = RecordedVideo(userCheck.id,channelRequest.id,channelRequest.channelName,channelRequest.topic,0,"")            db.session.add(newRecording)            db.session.commit()            return redirect('rtmp://' + sysSettings.siteAddress + '/streamrec-data/' + channelRequest.channelLoc, code=302)    else:        returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Failed Key Auth', 'key':str(key), 'ipAddress': str(ipaddress)}        print(returnMessage)        return abort(400)@app.route('/auth-user', methods=['POST'])def user_auth_check():    key = request.form['name']    ipaddress = request.form['addr']    requestedChannel = Channel.query.filter_by(channelLoc=key).first()    authedStream = Stream.query.filter_by(streamKey=requestedChannel.streamKey).first()    if authedStream is not None:        returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Successful Channel Auth', 'key': str(requestedChannel.streamKey), 'channelName': str(requestedChannel.channelName), 'ipAddress': str(ipaddress)}        print(returnMessage)        return 'OK'    else:        returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Failed Channel Auth. No Authorized Stream Key', 'channelName': str(key), 'ipAddress': str(ipaddress)}        print(returnMessage)        return abort(400)@app.route('/deauth-user', methods=['POST'])def user_deauth_check():    key = request.form['name']    ipaddress = request.form['addr']    authedStream = Stream.query.filter_by(streamKey=key).all()    channelRequest = Channel.query.filter_by(streamKey=key).first()    if authedStream is not []:        for stream in authedStream:            pendingVideo = RecordedVideo.query.filter_by(channelID=channelRequest.id, videoLocation="", pending=True).first()            if pendingVideo is not None:                pendingVideo.channelName = stream.streamName                pendingVideo.views = stream.totalViewers                pendingVideo.topic = stream.topic            db.session.delete(stream)            db.session.commit()            returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Stream Closed', 'key': str(key), 'channelName': str(channelRequest.channelName), 'userName':str(channelRequest.owningUser), 'ipAddress': str(ipaddress)}            print(returnMessage)        return 'OK'    else:        returnMessage = {'time': str(datetime.datetime.now()), 'status': 'Stream Closure Failure - No Such Stream', 'key': str(key), 'ipAddress': str(ipaddress)}        print(returnMessage)        return abort(400)@app.route('/recComplete', methods=['POST'])def rec_Complete_handler():    key = request.form['name']    path = request.form['path']    requestedChannel = Channel.query.filter_by(channelLoc=key).first()    pendingVideo = RecordedVideo.query.filter_by(channelID=requestedChannel.id, videoLocation="", pending=True).first()    videoPath = path.replace('/tmp/',requestedChannel.channelLoc + '/')    imagePath = videoPath.replace('.flv','.png')    videoPath = videoPath.replace('.flv','.mp4')    pendingVideo.thumbnailLocation = imagePath    pendingVideo.videoLocation = videoPath    pendingVideo.pending = False    db.session.commit()    return 'OK'@socketio.on('newViewer')def handle_new_viewer(streamData):    channelLoc = str(streamData['data'])    requestedChannel = Channel.query.filter_by(channelLoc=channelLoc).first()    stream = Stream.query.filter_by(streamKey=requestedChannel.streamKey).first()    viewedStream = Stream.query.filter_by(streamName=stream.streamName).first()    viewedStream.currentViewers = viewedStream.currentViewers + 1    db.session.commit()    join_room(streamData['data'])    if current_user.is_authenticated:        emit('message', {'msg': current_user.username + ' has entered the room.'}, room=streamData['data'])    else:        emit('message', {'msg': 'Guest has entered the room.'}, room=streamData['data'])@socketio.on('removeViewer')def handle_leaving_viewer(streamData):    channelLoc = str(streamData['data'])    requestedChannel = Channel.query.filter_by(channelLoc=channelLoc).first()    stream = Stream.query.filter_by(streamKey=requestedChannel.streamKey).first()    viewedStream = Stream.query.filter_by(streamName=stream.streamName).first()    viewedStream.currentViewers = viewedStream.currentViewers - 1    if viewedStream.currentViewers < 0:        viewedStream.currentViewers = 0    db.session.commit()    leave_room(streamData['data'])    if current_user.is_authenticated:        emit('message', {'msg': current_user.username + ' has left the room.'}, room=streamData['data'])    else:        emit('message', {'msg': 'Guest has left the room.'}, room=streamData['data'])@socketio.on('getViewerTotal')def handle_viewer_total_request(streamData):    channelLoc = str(streamData['data'])    requestedChannel = Channel.query.filter_by(channelLoc=channelLoc).first()    stream = Stream.query.filter_by(streamKey=requestedChannel.streamKey).first()    requestedStream = Stream.query.filter_by(streamName=stream.streamName).first()    emit('viewerTotalResponse', {'data':str(requestedStream.currentViewers)})socketio.on('disconnect')def disconnect(message):    logger.error(message)    emit('message', {'msg': message['msg']})@socketio.on('text')def text(message):    """Sent by a client when the user entered a new message.    The message is sent to all people in the room."""    room = message['room']    emit('message', {'msg': current_user.username + ': ' + message['msg']}, room=room)@socketio.on('getServerResources')def get_resource_usage():    cpuUsage = psutil.cpu_percent(interval=1)    memoryUsage = psutil.virtual_memory()    emit('serverResources',{'cpuUsage':cpuUsage,'memoryUsage':memoryUsage})init_db_values()if __name__ == '__main__':    app.jinja_env.auto_reload = True    app.config['TEMPLATES_AUTO_RELOAD'] = True    socketio.run(app)