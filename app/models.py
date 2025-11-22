from datetime import datetime, timezone
from werkzeug.security import generate_password_hash
import uuid

def user_model(data):
    return {
        "_id": f"u_{uuid.uuid4().hex[:8]}",
        "username": data["username"],
        "password_hash": generate_password_hash(data["password"]),
        "name": data["name"],
        "email": data["email"] if "email" in data else None,
        "phone": data["phone"] if "phone" in data else None,
        "is_verified": False,
        "is_verified_ngo": False,
        "last_active_location": data["location"] if "location" in data else {"lat": None, "lon": None},
        "registered_at": datetime.utcnow().isoformat(),
        "is_active": True, # if violations reach a threshold account will be blocked...
        "roles": ["user"],
        "meta": {
            "profile_completed": bool(data.get("email") or data.get("phone")),
            "total_requests_made": 0,
            "total_requests_served": 0,
            "total_false_requests_made": 0,
            "total_active_requests": 0  # cap of 3...
        }
    }

def user_disaster_model(data):
    return {
        "_id": str(uuid.uuid4()),
        "username": data["username"],
        "phone": data["phone"],
        "latitude": float(data["latitude"]),
        "longitude": float(data["longitude"]),
        "message": data["message"] if "message" in data else "",
        "disaster_type": data["disaster_type"] if "disaster_type" in data else "",
        "created_at": datetime.utcnow().isoformat(),
        "is_resolved": False,
        "priority_count": 1,
        "priority_updated_at": datetime.now(timezone.utc).isoformat(),
        "active_responders": [] # each {"username": str, "phone": str, "email": str}
    }