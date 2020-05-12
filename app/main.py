import os
import uvicorn

from sanic import Sanic
from sanic_session import Session
from sanic_cors import CORS, cross_origin

from functools import partial

from .routes import app_routes

from .db.dbListeners import start_db, stop_db

from .workers.listeners import create_task_queue
from .helpers import random_string
from .config import configSwitch

# Need to turn this off in production
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Sanic(__name__)
CORS(app)


app_config = configSwitch(os.getenv('ENV_NAME'))
app.config.from_object(app_config)
app.config.OAUTH_VERIFIER = random_string(40)

app.register_listener(start_db, 'after_server_start')
app.register_listener(create_task_queue, 'after_server_start')
app.register_listener(stop_db, 'before_server_stop')

app.blueprint(app_routes)

