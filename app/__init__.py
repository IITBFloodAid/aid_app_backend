from flask import Flask
from .database import init_db

def create_app():
    app = Flask(__name__)
    init_db(app)

    from app.auth_service import auth
    app.register_blueprint(auth, url_prefix='/auth')
    
    return app