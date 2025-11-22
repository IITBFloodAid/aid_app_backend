from flask import Blueprint

info = Blueprint('info', __name__)

from app.info_service import routes 