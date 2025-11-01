from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import InternalServerError
from app.database import mongo

DB_FILE = 'users_db.json'

def read_db():
    try:
        docs = mongo.db.users.find({}, {"_id": 0})
        return docs
    except Exception as e:
        print(e)
        raise InternalServerError(description=f"Database read failed: {e}")

def write_db(username: str, password: str):
    try:
        hashed_pw = generate_password_hash(password)
        user_doc = {
            "username": username,
            "password_hash": hashed_pw
        }
        mongo.db.users.insert_one(user_doc)
    except Exception as e:
        print(e)
        raise InternalServerError(description=f"Database write failed: {e}")

def validate_user(username, password):
    try:
        users = read_db()
        for user in users:
            if user['username'] == username and check_password_hash(user["password_hash"], password):
                return True
        return False
    except Exception as e:
        print(e)
        raise InternalServerError(description=f"Validation check failed: {e}")