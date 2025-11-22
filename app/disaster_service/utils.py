from werkzeug.exceptions import InternalServerError
from app.database import mongo
from typing import List
from rapidfuzz import fuzz
from math import radians, cos, sin, asin, sqrt

def find_request(key_name: str, value: str):
    try:
        req = list(mongo.db.disaster_requests.find({key_name: value}))
        return req
    except Exception as e:
        raise InternalServerError(description = f"Request search failed: {e}")
    
def write_request(disaster_doc: dict):
    try:
        mongo.db.disaster_requests.insert_one(disaster_doc)
    except Exception as e:
        raise InternalServerError(description = f"Database write failed: {e}")
    
def update_request(id: str, keys: List[str], values):
    try:
        for index, key_name in enumerate(keys):
            mongo.db.disaster_requests.update_one(
                {"_id": id},
                {"$set": {key_name: values[index]}}
            )
    except Exception as e:
        raise InternalServerError(description=f"Update failed: {e}")
    
def add_responders(id: str, values):
    try:
        mongo.db.disaster_requests.update_one(
            {"_id": id},
            {"$push": {"active_responders": values}}
        )
    except Exception as e:
        raise InternalServerError(description=f"Failed to add active responder: {e}")
    
def delete_request(id: str):
    try:
        result = mongo.db.disaster_requests.delete_one({"_id": id})
        return result.deleted_count
    except Exception as e:
         raise InternalServerError(description=f"Failed to delete the request: {e}")
    
def extract_first_coordinate(polygon_text):
    """Extract the first coordinate pair from cap:polygon (space-separated pairs)"""
    if not polygon_text:
        return None
    
    # Split by spaces to get the first coordinate pair
    first_pair = polygon_text.strip().split()[0]  # first item separated by space
    lat_lon = first_pair.split(",")
    
    if len(lat_lon) == 2:
        return (float(lat_lon[0].strip()), float(lat_lon[1].strip()))
    
    return None

def is_english(text: str) -> bool:
    """Return True if the text is mostly ASCII (basic English check)."""
    try:
        text.encode(encoding='ascii')
    except UnicodeEncodeError:
        return False
    return True

def get_unique_disaster_list(temp: dict):
    unique = {}  # title -> link

    for title, link in temp.items():
        if not is_english(title):
            continue 

        keep = True
        for u_title in list(unique.keys()):
            # Check similarity
            if fuzz.token_set_ratio(title, u_title) >= 80:
                keep = False
                break
        if keep:
            unique[title] = link
    
    return unique

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points
    on the Earth specified in decimal degrees.
    Returns distance in kilometers.
    """
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Earth's radius in km
    return c * r

def sort_alerts_by_proximity(alerts: list, target_lat: float, target_lon: float):
    """
    Sort a list of disaster alerts by proximity to a given latitude/longitude.

    Args:
        alerts (list): List of dicts, each must have 'first_coord' as [lat, lon] or None
        target_lat (float): Latitude to sort by
        target_lon (float): Longitude to sort by

    Returns:
        list: Sorted list of alerts (without 'first_coord')
    """
    for alert in alerts:
        coord = alert["first_coord"]
        if coord and len(coord) == 2:
            alert["distance"] = haversine(coord[0], coord[1], target_lat, target_lon)
        else:
            alert["distance"] = float("inf")  # unknown or malformed location goes to the end

    # Sort by distance
    alerts.sort(key=lambda x: x["distance"])

    # # Remove 'first_coord' and 'distance' from final output
    for alert in alerts:
        alert.pop("first_coord", None)
        alert.pop("distance", None)

    return alerts