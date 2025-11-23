from flask_pymongo import PyMongo
from dotenv import load_dotenv
import os

load_dotenv() # kept for the dev purposes...
mongo = PyMongo()

def init_db(app):
    app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
    mongo.init_app(app)