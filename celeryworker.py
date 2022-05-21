from gevent import monkey
monkey.patch_all(thread=True)

from flask import Flask
from celery.signals import worker_process_init, worker_process_shutdown

from conf import config
from globals import globalvars

app = Flask(__name__)
app.config['WEB_ROOT'] = globalvars.videoRoot
app.config['SQLALCHEMY_DATABASE_URI'] = config.dbLocation
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_MAX_OVERFLOW'] = -1
app.config['SQLALCHEMY_POOL_RECYCLE'] = 300
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 600
app.config['MYSQL_DATABASE_CHARSET'] = "utf8"
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'encoding': 'utf8', 'pool_use_lifo': 'False', 'pool_size': 10, "pool_pre_ping": True}
app.config['VIDEO_UPLOAD_TEMPFOLDER'] = app.config['WEB_ROOT'] + 'videos/temp'
app.config["VIDEO_UPLOAD_EXTENSIONS"] = ["PNG", "MP4"]

"""
Initialize Celery
"""
RedisURL = None
if config.redisPassword == '' or config.redisPassword is None:
    RedisURL = "redis://" + config.redisHost + ":" + str(config.redisPort)
else:
    RedisURL = "redis://:" + config.redisPassword + "@" + config.redisHost + ":" + str(config.redisPort)

app.config['broker_url'] = RedisURL
app.config['result_backend'] = RedisURL

from classes.shared import celery
from functions.scheduled_tasks import video_tasks

celery.conf.broker_url = app.config['broker_url']
celery.conf.result_backend = app.config['result_backend']
celery.conf.update(app.config)


class ContextTask(celery.Task):
    """Make celery tasks work with Flask app context"""

    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)


celery.Task = ContextTask

"""
Global Caching
"""

from classes.shared import cache
redisCacheOptions = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_KEY_PREFIX': 'OSP_FC',
    'CACHE_REDIS_HOST': config.redisHost,
    'CACHE_REDIS_PORT': config.redisPort,
}
if config.redisPassword != '' and config.redisPassword is not None:
    redisCacheOptions['CACHE_REDIS_PASSWORD'] = config.redisPassword
cache.init_app(app, config=redisCacheOptions)


"""
Handle Celery Worker DB Connection Handling on Start and Shutdown
"""
db_conn = None
@worker_process_init.connect
def init_worker(**kwargs):
    global db_conn
    print('Initializing database connection for worker.')

    from classes.shared import db

    db.init_app(app)
    db.app = app
    db_conn = db


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    global db_conn
    if db_conn:
        print('Closing database connectionn for worker.')
        db_conn.session.close()
        db_conn.get_engine(app).dispose()

if __name__ == '__main__':
    celery.worker_main()
