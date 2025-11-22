from app.auth_service import auth
from flask import request, jsonify, current_app
from app.auth_service.utils import validate_user, read_db, write_db, find_user, update_db, generate_otp, store_otp, check_otp, is_ngo_email, send_otp_email
from werkzeug.exceptions import InternalServerError, BadRequest, Conflict
from app.models import user_model
from datetime import datetime

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
            user = find_user(username)
            if user['is_active'] != True:
                return jsonify({"message": "Account is deactivated for some reason"}), 403
            user['last_login'] = datetime.utcnow().isoformat()
            update_db(id_key='_id',id_value=user['_id'], key_name='last_login', value=datetime.utcnow().isoformat())
            return jsonify({
                "message": "Login successful",
                "username": username,
                "verified": user['is_verified']
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
            return jsonify({
                "message": "Username and password are required"
            }), 400

        users = read_db()
        if any(user['username'] == username for user in users):
            return jsonify({"message": "Username already exists"}), 409

        # consider user document using user model...
        user_doc = user_model(data)
        write_db(user_doc)
        return jsonify({
            "message": "Registration successful",
            "username": username,
            "verified": False,
            "email": data['email'] 
        }), 200
    except Exception as e:
        print(e)
        raise InternalServerError(description=f"Registration failed: {e}")

# to mark a user verified from a ngo
@auth.route('/verification/send_otp', methods=['POST'])
def send_otp_ngo():
    try:
        ngo = request.args.get("ngo") # as a query param...
        data = request.get_json()
        if not data:
            raise BadRequest("Missing JSON body")
        
        username = data['username']
        user = find_user(username)
        email = user['email']
        if not username or not email:
            return jsonify({
                "message": "Username is required",
                "email": "Email is required"
            }), 400
        
        otp, hashed, expiry = generate_otp()
        user = find_user(username)
        if ngo is None:
            send_otp_email(user['email'], otp)
            store_otp(username, hashed, expiry, "email")
            return jsonify({
                    "message": f"OTP on {email} has been sent, please enter in next 5 minutes"
                }), 200
        else:
            if is_ngo_email(email):
                send_otp_email(user['email'], otp)
                store_otp(username, hashed, expiry, "email")
                return jsonify({
                    "message": f"OTP on {email} has been sent, please enter in next 5 minutes"
                }), 200
            else:
                return jsonify({
                    "message": "Sorry, your email is not from an approved NGO domain. Please contact the administrators if you believe your domain should be added to the accepted list."
                }), 400
    except Exception as e:
        print(e)
        raise InternalServerError(description=f"failed to send OTP: {e}")

@auth.route('/verification/verify_otp', methods=['POST'])
def verify_otp_ngo():
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("Missing JSON body")
        
        otp = data['otp']
        username = data['username']

        if not otp or not username:
            return jsonify({
                "message": "OTP is required"
            }), 400
        
        if check_otp(username, otp, "email"):
            update_db("username", username, "is_verified_ngo", True)
            return jsonify({
                "message": "Your profile has been marked under verified NGO."
            }), 200
        else:
            return jsonify({
                "message": "OTP verification has failed for NGO."
            }), 400
    except Exception as e:
        print(e)
        raise InternalServerError(description=f"failed to verify the otp: {e}")

# ### put this function in utils somewhere ###
# @auth.route("/update_user_location", methods=["POST"])
# def update_location():
#     try:
#         data = request.get_json()
#         username = data["username"]
#         lat = data["lat"]
#         lon = data["lon"]
#         if not username or lat is None or lon is None:
#             return jsonify({"error": "Missing location or username"}), 400
        
#         value = {"lat": float(lat), "lon": float(lon), "source": "ip_based"}
#         update_db("username", username, "last_active_location", value)
#         return jsonify({"message": f"{username}'s location has been updated."})
#     except Exception as e:
#         raise InternalServerError(description=f"Failed to update the location: {e}")