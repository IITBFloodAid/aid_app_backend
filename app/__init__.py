from flask import Flask
from .database import init_db
from flask_cors import CORS
from .config import *

def create_app():
    app = Flask(__name__)

    CORS(app)
    init_db(app)
    app.config["SECRET_KEY"] = SECRET_KEY
    
    from app.auth_service import auth
    from app.disaster_service import disaster
    from app.info_service import info
    from app.llm_service import llm
    from app.map_service import map
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(disaster, url_prefix='/disaster')
    app.register_blueprint(info, url_prefix='/info')
    app.register_blueprint(llm, url_prefix='/llm')
    app.register_blueprint(map, url_prefix='/map')
    
    return app