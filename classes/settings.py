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
    restreamMaxBitrate = db.Column(db.Integer)
    serverMessageTitle = db.Column(db.String(256))
    serverMessage = db.Column(db.String(2048))

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
        self.background = "Ash"
        self.systemTheme = "Defaultv2"
        self.version = version
        self.systemLogo = "/static/img/logo.png"
        self.serverMessageTitle = "Server Message"
        self.serverMessage = ""
        self.restreamMaxBitrate = 3500
        self.protectionEnabled = False

    def __repr__(self):
        return '<id %r>' % self.id

    def serialize(self):
        return {
            'siteName': self.siteName,
            'siteProtocol': self.siteProtocol,
            'siteAddress': self.siteAddress,
            'siteURI': self.siteProtocol + self.siteAddress,
            'siteLogo': self.systemLogo,
            'serverMessage': self.serverMessage,
            'allowRecording': self.allowRecording,
            'allowUploads': self.allowUploads,
            'allowComments': self.allowComments,
            'version': self.version,
            'protectionEnabled': self.protectionEnabled
        }