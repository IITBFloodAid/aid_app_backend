from app.info_service import info
from werkzeug.exceptions import InternalServerError
from flask import request
from app.info_service.utils import find_valid_requests, find_common_requests
from app.auth_service.utils import find_user

@info.route("/get_requests/<string:username>", methods=["GET"]) # all open/closed requests made by the user...
def get_all_open_requests_by_user(username):
    try:
        opened = request.args.get("opened")
        is_resolved = True
        if opened=="1":
            is_resolved = False
        open_requests = find_valid_requests(username, is_resolved)
        return open_requests 
    except Exception as e:
        print(e)
        raise InternalServerError(description=f"Failed to fetch all open requests: {e}")
    
@info.route("/get_common_requests", methods=["GET"]) # all open common requests...
def get_common_requests():
    try:
        open_common_requests = find_common_requests()
        return open_common_requests 
    except Exception as e:
        print(e)
        raise InternalServerError(description=f"Failed to fetch all open requests: {e}")

@info.route("/get_user_detail/<string:username>", methods=["GET"])
def get_users_details(username):
    try:
        user_details = find_user(username)
        for key in ["_id", "password_hash", "roles"]:
            del user_details[key]
        return user_details
    except Exception as e:
        print(e)
        raise InternalServerError(description="Failed to fetch data for the user: {e}")