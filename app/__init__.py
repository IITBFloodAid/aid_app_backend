from flask import Flask
from .database import init_db
from flask_cors import CORS

def create_app():
    app = Flask(__name__)

    CORS(app)
    init_db(app)

    from app.auth_service import auth
    app.register_blueprint(auth, url_prefix='/auth')
    
    return app