from .shared import db

class settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    siteName = db.Column(db.String(255))
    siteProtocol = db.Column(db.String(24))
    siteAddress = db.Column(db.String(255))
    serverTimeZone = db.Column(db.String(255))
    allowRecording = db.Column(db.Boolean)
    allowUploads = db.Column(db.Boolean)
    allowRestream = db.Column(db.Boolean)
    protectionEnabled = db.Column(db.Boolean)
    adaptiveStreaming = db.Column(db.Boolean)
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
    limitMaxChannels = db.Column(db.Integer)
    proxyFQDN = db.Column(db.String(2048))
    maintenanceMode = db.Column(db.Boolean)
    buildEdgeOnRestart = db.Column(db.Boolean)
    hubUUID = db.Column(db.String(255))
    hubEnabled = db.Column(db.Boolean)
    hubURL = db.Column(db.String(255))
    maxVideoRetention = db.Column(db.Integer)

    def __init__(self, siteName, siteProtocol, siteAddress, allowRecording, allowUploads, adaptiveStreaming, showEmptyTables, allowComments, version):
        self.siteName = siteName
        self.siteProtocol = siteProtocol
        self.siteAddress = siteAddress
        self.serverTimeZone = "UTC"
        self.allowRecording = allowRecording
        self.allowUploads = allowUploads
        self.allowRestream = True
        self.adaptiveStreaming = adaptiveStreaming
        self.showEmptyTables = showEmptyTables
        self.allowComments = allowComments
        self.sortMainBy = 0
        self.systemTheme = "Defaultv3"
        self.version = version
        self.systemLogo = "/static/img/nav-logo.png"
        self.systemLogoLight = "/static/img/logo-light.png"
        self.serverMessageTitle = "Server Message"
        self.serverMessage = ""
        self.restreamMaxBitrate = 3500
        self.maxClipLength = 90
        self.limitMaxChannels = 0
        self.buildEdgeOnRestart = True
        self.protectionEnabled = False
        self.maintenanceMode = False
        self.hubEnabled = False
        self.hubURL = "https://hub.openstreamingplatform.com"
        self.maxVideoRetention = 0
        #self.terms = ''
        #self.privacy = ''

    def __repr__(self):
        return '<id %r>' % self.id

    def serialize(self):
        return {
            'siteName': self.siteName,
            'siteProtocol': self.siteProtocol,
            'siteAddress': self.siteAddress,
            'serverTimeZone': self.serverTimeZone,
            'siteURI': self.siteProtocol + self.siteAddress,
            'siteLogo': self.systemLogo,
            'serverMessageTitle': self.serverMessageTitle,
            'serverMessage': self.serverMessage,
            'allowRecording': self.allowRecording,
            'allowUploads': self.allowUploads,
            'allowRestream' : self.allowRestream,
            'allowComments': self.allowComments,
            'version': self.version,
            'restreamMaxBitRate': self.restreamMaxBitrate,
            'maxClipLength': self.maxClipLength,
            'protectionEnabled': self.protectionEnabled,
            'adaptiveStreaming': self.adaptiveStreaming,
            'maintenanceMode': self.maintenanceMode,
            'hubEnabled': self.hubEnabled,
            'hubURL': self.hubURL,
            'maxVideoRetention': self.maxVideoRetention
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
    hide = db.Column(db.Boolean)
    streams = db.relationship('Stream', backref='server', cascade="all, delete-orphan", lazy="joined")

    def __init__(self, address):
        self.address = address
        self.hide = False
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

class static_page(db.Model):
    __tablename__ = "static_page"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), unique=True)
    title = db.Column(db.String(256))
    iconClass = db.Column(db.String(256))
    content = db.Column(db.Text)
    isTopBar = db.Column(db.Boolean)

    def __init__(self, url, icon, title):
        self.name = url
        self.title = title
        self.iconClass = icon
        self.isTopBar = False

    def __repr__(self):
        return '<id %r>' % self.id
