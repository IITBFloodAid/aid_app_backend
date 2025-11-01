from flask import Blueprint

auth = Blueprint('auth', __name__)

from app.auth_service import routes  # by this routes.py has been executed and routes are registered