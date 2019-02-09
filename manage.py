from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from conf import config

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.dbLocation

db = SQLAlchemy(app)
migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)

from classes import Stream.Stream
from classes import Channel.Channel
from classes import dbVersion.dbVersion
from classes import RecordedVideo.RecordedVideo
from classes import topics.topics
from classes import settings.settings
from classes import banList.banList
from classes import Sec.Role
from classes import Sec.Users

from classes import upvotes.upvotes
from classes import apikey.apikey

if __name__ == '__main__':
    manager.run()
