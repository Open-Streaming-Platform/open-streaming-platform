from .shared import db

class settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    siteName = db.Column(db.String(255))
    siteAddress = db.Column(db.String(255))
    smtpAddress = db.Column(db.String(255))
    smtpPort = db.Column(db.Integer)
    smtpTLS = db.Column(db.Boolean)
    smtpSSL = db.Column(db.Boolean)
    smtpUsername = db.Column(db.String(255))
    smtpPassword = db.Column(db.String(255))
    smtpSendAs = db.Column(db.String(255))
    allowRegistration = db.Column(db.Boolean)
    requireConfirmedEmail = db.Column(db.Boolean)
    allowRecording = db.Column(db.Boolean)
    allowUploads = db.Column(db.Boolean)
    adaptiveStreaming = db.Column(db.Boolean)
    background = db.Column(db.String(255))
    showEmptyTables = db.Column(db.Boolean)
    allowComments = db.Column(db.Boolean)
    systemTheme = db.Column(db.String(255))
    systemLogo = db.Column(db.String(255))
    version = db.Column(db.String(255))
    serverMessage = db.Column(db.String(2048))

    def __init__(self, siteName, siteAddress, smtpAddress, smtpPort, smtpTLS, smtpSSL, smtpUsername, smtpPassword, smtpSendAs, allowRegistration, requireConfirmedEmail, allowRecording, allowUploads, adaptiveStreaming, showEmptyTables, allowComments, version):
        self.siteName = siteName
        self.siteAddress = siteAddress
        self.smtpAddress = smtpAddress
        self.smtpPort = smtpPort
        self.smtpTLS = smtpTLS
        self.smtpSSL = smtpSSL
        self.smtpUsername = smtpUsername
        self.smtpPassword = smtpPassword
        self.smtpSendAs = smtpSendAs
        self.allowRegistration = allowRegistration
        self.requireConfirmedEmail = requireConfirmedEmail
        self.allowRecording = allowRecording
        self.allowUploads = allowUploads
        self.adaptiveStreaming = adaptiveStreaming
        self.showEmptyTables = showEmptyTables
        self.allowComments = allowComments
        self.background = "Ash"
        self.systemTheme = "Defaultv2"
        self.version = version
        self.systemLogo = "/static/img/logo.png"
        self.serverMessage = ""

    def __repr__(self):
        return '<id %r>' % self.id

    def serialize(self):
        return {
            'siteName': self.siteName,
            'siteAddress': self.siteAddress,
            'siteLogo': self.systemLogo,
            'serverMessage': self.serverMessage,
            'allowRegistration': self.allowRegistration,
            'allowRecording': self.allowRecording,
            'allowUploads': self.allowUploads,
            'allowComments': self.allowComments,
            'version': self.version
        }