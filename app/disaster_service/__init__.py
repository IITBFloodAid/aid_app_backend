from flask import Blueprint

disaster = Blueprint('disaster', __name__)

from app.disaster_service import routes  # by this routes.py has been executed and routes are registered