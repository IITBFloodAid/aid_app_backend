from flask import Blueprint

map = Blueprint('map', __name__)

from app.map_service import routes  # by this routes.py has been executed and routes are registered