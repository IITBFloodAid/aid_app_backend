from app.auth_service import auth
from flask import request, render_template, jsonify
from app.auth_service.utils import validate_user, read_db, write_db
from werkzeug.exceptions import InternalServerError, BadRequest, Conflict, Unauthorized

@auth.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("Missing JSON body")

        username = data['username']
        password = data['password']

        if not username or not password:
            raise BadRequest("Username and password are required")

        if validate_user(username, password):
            return jsonify({
                "message": "Login successful",
                "username": username
            }), 200
        else:
            return jsonify({
                "message": "Invalid Credentials"
            }), 401
    except (BadRequest, Conflict) as e:
        raise e 
    except Exception as e:
        print(e)
        raise InternalServerError(description=f"Login failed: {e}")

@auth.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("Missing JSON body")
        
        username = data['username']
        password = data['password']

        if not username or not password:
            raise BadRequest("Username and password are required")

        users = read_db()
        if any(user['username'] == username for user in users):
            raise Conflict("Username already exists")

        write_db(username, password)
        return jsonify({
            "message": "Registration successful",
            "username": username
        }), 201
    except (BadRequest, Conflict) as e:
        raise e
    except Exception as e:
        print(e)
        raise InternalServerError(description=f"Registration failed: {e}")