from sanic import Blueprint
from sanic.response import redirect, html, json

from app.workers.mediators import AuthMediator
from app.db import TaskTypes

from .base import base_bp
from .tasks import api_routes

app_routes = Blueprint.group(base_bp, api_routes)
