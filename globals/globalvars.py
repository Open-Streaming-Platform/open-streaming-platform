version = "0.9.4"
appDBVersion = 0.90
processUUID = None

RedisURL = None

videoRoot = "/var/www/"

# Default XMPP Create Rules Settings
room_config = {
    "persistent": "true",
    "moderated": "true",
    "members_by_default": "true",
    "max_users": "2500",
    "allow_change_subj": "false",
    "allow_private_messages_from_visitors": "nobody",
    "allow_visitor_status": "false",
    "allow_visitor_nickchange": "false",
}

# Global oAuth Dictionary
oAuthProviderObjects = {}

# Current Theme Settings Data
themeData = {}

# In-Memory Cache of Topic Names
topicCache = {}

# Create In-Memory Invite Cache to Prevent High CPU Usage for Polling Channel Permissions during Streams
inviteCache = {}

# Build Channel Restream Subprocess Dictionary
restreamSubprocesses = {}

# Build Edge Restream Subprocess Dictionary
activeEdgeNodes = []
edgeRestreamSubprocesses = {}

# ejabberd Server Configuration
ejabberdServer = "127.0.0.1"
ejabberdServerHttpBindFQDN = None

recaptchaEnabled = False
RECAPTCHA_PUBLIC_KEY = ""
RECAPTCHA_PRIVATE_KEY = ""

# Restart Required Variable
restartRequired = False
