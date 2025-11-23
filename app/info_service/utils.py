from werkzeug.exceptions import InternalServerError
from app.database import mongo
from typing import List
from app.disaster_service.utils import haversine

def find_valid_requests(username: str, is_resolved):
    try:
        open_requests = mongo.db.disaster_requests.find(
            {
                "username": username,
                "is_resolved": is_resolved
            },
            {
                "_id": 1,
                "username": 1,
                "phone": 1,
                "message": 1,
                "disaster_type": 1,
                "created_at": 1,
                "priority_count": 1,
                "priority_updated_at": 1,
                "active_responders": 1,
                "latitude": 1,
                "longitude": 1,
                "location": 1,
                "location_hint": 1
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
                "_id": 1,
                "username": 1,
                "phone": 1,
                "message": 1,
                "disaster_type": 1,
                "created_at": 1,
                "priority_count": 1,
                "priority_updated_at": 1,
                "active_responders": 1,
                "latitude": 1,
                "longitude": 1,
                "location": 1,
                "location_hint": 1
            }
        )
        return list(open_requests)
    except Exception as e:
        raise InternalServerError(description=f"Search failed: {e}")
    
def sort_alerts_by_proximity(open_common_requests: list, target_lat: float, target_lon: float):
    for request in open_common_requests:
        if request["latitude"] and request["longitude"]:
            request["distance"] = haversine(request["latitude"], request["longitude"], target_lat, target_lon)
        else:
            request["distance"] = float("inf")  # unknown or malformed location goes to the end

    # Sort by distance
    open_common_requests.sort(key=lambda x: x["distance"])
    return open_common_requests