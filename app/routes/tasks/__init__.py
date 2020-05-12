from sanic import Blueprint

from .gmail_tasks import gmail_bp
from .hermes_tasks import hermes_bp
from .form_routes import form_bp

task_routes = Blueprint.group(gmail_bp, hermes_bp)
api_routes = Blueprint.group(task_routes, form_bp, url_prefix='/api')
