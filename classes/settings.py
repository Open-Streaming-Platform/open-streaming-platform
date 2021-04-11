from .shared import db

class settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    siteName = db.Column(db.String(255))
    siteProtocol = db.Column(db.String(24))
    siteAddress = db.Column(db.String(255))
    smtpAddress = db.Column(db.String(255))
    smtpPort = db.Column(db.Integer)
    smtpTLS = db.Column(db.Boolean)
    smtpSSL = db.Column(db.Boolean)
    smtpUsername = db.Column(db.String(255))
    smtpPassword = db.Column(db.String(255))
    smtpSendAs = db.Column(db.String(255))
    allowRecording = db.Column(db.Boolean)
    allowUploads = db.Column(db.Boolean)
    protectionEnabled = db.Column(db.Boolean)
    adaptiveStreaming = db.Column(db.Boolean)
    background = db.Column(db.String(255))
    showEmptyTables = db.Column(db.Boolean)
    allowComments = db.Column(db.Boolean)
    systemTheme = db.Column(db.String(255))
    systemLogo = db.Column(db.String(255))
    version = db.Column(db.String(255))
    sortMainBy = db.Column(db.Integer)
    restreamMaxBitrate = db.Column(db.Integer)
    serverMessageTitle = db.Column(db.String(256))
    serverMessage = db.Column(db.String(8192))
    maxClipLength = db.Column(db.Integer)
    proxyFQDN = db.Column(db.String(2048))
    maintenanceMode = db.Column(db.Boolean)
    buildEdgeOnRestart = db.Column(db.Boolean)
    allowRegistration = db.Column(db.Boolean) # Moved to config.py
    requireConfirmedEmail = db.Column(db.Boolean) # Moved to config.py

    def __init__(self, siteName, siteProtocol, siteAddress, smtpAddress, smtpPort, smtpTLS, smtpSSL, smtpUsername, smtpPassword, smtpSendAs, allowRecording, allowUploads, adaptiveStreaming, showEmptyTables, allowComments, version):
        self.siteName = siteName
        self.siteProtocol = siteProtocol
        self.siteAddress = siteAddress
        self.smtpAddress = smtpAddress
        self.smtpPort = smtpPort
        self.smtpTLS = smtpTLS
        self.smtpSSL = smtpSSL
        self.smtpUsername = smtpUsername
        self.smtpPassword = smtpPassword
        self.smtpSendAs = smtpSendAs
        self.allowRecording = allowRecording
        self.allowUploads = allowUploads
        self.adaptiveStreaming = adaptiveStreaming
        self.showEmptyTables = showEmptyTables
        self.allowComments = allowComments
        self.sortMainBy = 0
        self.background = "Ash"
        self.systemTheme = "Defaultv2"
        self.version = version
        self.systemLogo = "/static/img/logo.png"
        self.serverMessageTitle = "Server Message"
        self.serverMessage = ""
        self.restreamMaxBitrate = 3500
        self.maxClipLength = 90
        self.buildEdgeOnRestart = True
        self.protectionEnabled = False
        self.maintenanceMode = False

    def __repr__(self):
        return '<id %r>' % self.id

    def serialize(self):
        return {
            'siteName': self.siteName,
            'siteProtocol': self.siteProtocol,
            'siteAddress': self.siteAddress,
            'siteURI': self.siteProtocol + self.siteAddress,
            'siteLogo': self.systemLogo,
            'serverMessageTitle': self.serverMessageTitle,
            'serverMessage': self.serverMessage,
            'allowRecording': self.allowRecording,
            'allowUploads': self.allowUploads,
            'allowComments': self.allowComments,
            'version': self.version,
            'restreamMaxBitRate': self.restreamMaxBitrate,
            'maxClipLength': self.maxClipLength,
            'protectionEnabled': self.protectionEnabled,
            'adaptiveStreaming': self.adaptiveStreaming,
            'maintenanceMode': self.maintenanceMode
        }

class edgeStreamer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(1024))
    port = db.Column(db.Integer)
    active = db.Column(db.Boolean)
    status = db.Column(db.Integer)
    loadPct = db.Column(db.Integer)

    def __init__(self, address, port, loadPct):
        self.address = address
        self.active = False
        self.status = 0
        self.port = port
        self.loadPct = loadPct

    def __repr__(self):
        return '<id %r>' % self.id

    def serialize(self):
        return {
            'id': self.id,
            'address': self.address,
            'port': self.port,
            'active': self.active,
            'status': self.status,
            'loadPct': self.loadPct
        }

class rtmpServer(db.Model):
    __tablename__ = "rtmpServer"
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(1024))
    active = db.Column(db.Boolean)
    streams = db.relationship('Stream', backref='server', cascade="all, delete-orphan", lazy="joined")

    def __init__(self, address):
        self.address = address
        self.active = True

    def __repr__(self):
        return '<id %r>' % self.id

    def serialize(self):
        return {
            'id': self.id,
            'address': self.address,
            'active': self.active
        }

class oAuthProvider(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40))
    friendlyName = db.Column(db.String(64))
    preset_auth_type = db.Column(db.String(64))
    displayColor = db.Column(db.String(8))
    client_id = db.Column(db.String(256))
    client_secret = db.Column(db.String(256))
    access_token_url = db.Column(db.String(1024))
    access_token_params = db.Column(db.String(1024))
    authorize_url = db.Column(db.String(1024))
    authorize_params = db.Column(db.String(1024))
    api_base_url = db.Column(db.String(1024))
    client_kwargs = db.Column(db.String(2056))
    profile_endpoint = db.Column(db.String(2056))
    id_value = db.Column(db.String(256))
    username_value = db.Column(db.String(256))
    email_value = db.Column(db.String(256))

    def __init__(self, name, preset_auth_type, friendlyName, displayColor, client_id, client_secret, access_token_url, authorize_url, api_base_url, profile_endpoint, id_value, username_value, email_value):
        self.name = name
        self.preset_auth_type = preset_auth_type
        self.friendlyName = friendlyName
        self.displayColor = displayColor
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token_url = access_token_url
        self.authorize_url = authorize_url
        self.api_base_url = api_base_url
        self.profile_endpoint = profile_endpoint
        self.id_value = id_value
        self.username_value = username_value
        self.email_value = email_value

    def __repr__(self):
        return '<id %r>' % self.id