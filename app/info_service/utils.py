from werkzeug.exceptions import InternalServerError
from app.database import mongo
from typing import List

def find_valid_requests(username: str, is_resolved):
    try:
        open_requests = mongo.db.disaster_requests.find(
            {
                "username": username,
                "is_resolved": is_resolved
            },
            {
                "_id": 0,
                "username": 1,
                "phone": 1,
                "message": 1,
                "disaster_type": 1,
                "created_at": 1,
                "priority_updated_at": 1,
                "active_responders": 1
            }
        )
        return list(open_requests)
    except Exception as e:
        raise InternalServerError(description=f"Search failed: {e}")
    
def find_common_requests():
    try:
        open_requests = mongo.db.disaster_requests.find(
            {
                "is_resolved": False
            },
            {
                "_id": 0,
                "username": 1,
                "phone": 1,
                "message": 1,
                "disaster_type": 1,
                "created_at": 1,
                "priority_updated_at": 1,
                "active_responders": 1
            }
        )
        return list(open_requests)
    except Exception as e:
        raise InternalServerError(description=f"Search failed: {e}")