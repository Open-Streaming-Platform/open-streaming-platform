from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from flask_socketio import SocketIO
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cache import Cache

db = SQLAlchemy()
oauth = OAuth()
socketio = SocketIO()
email = Mail()
cache = Cache()
limiter = Limiter(key_func=get_remote_address)
