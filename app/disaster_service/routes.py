from app.disaster_service import disaster
from flask import request, jsonify, current_app
from werkzeug.exceptions import InternalServerError, BadRequest
from app.models import user_disaster_model
from datetime import datetime, timedelta, timezone
import requests
import xml.etree.ElementTree as ET
from app.disaster_service.utils import find_request, write_request, update_request, add_responders, delete_request, extract_first_coordinate, get_unique_disaster_list, sort_alerts_by_proximity, dump_alerts_to_json, read_alerts_from_json
from app.auth_service.utils import find_user, update_db

SACHET_FEED_URL = "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml"

@disaster.route("/get_data", methods=["POST"])
def get_disasters():
    try:
        data = request.get_json() # returns a python dict...
        if not data:
            return jsonify({"error": "No JSON body found"}), 400
        
        latitude = data["latitude"]
        longitude = data["longitude"]

        unique_alerts = read_alerts_from_json()
        unique_alerts = sort_alerts_by_proximity(unique_alerts, latitude, longitude)
        # Return as JSON
        return jsonify(unique_alerts), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@disaster.route("/cron_job", methods=["GET"])
def make_json_disasters():
    try:
        # Fetch the CAP feed
        response = requests.get(SACHET_FEED_URL)
        response.raise_for_status() # raise an exception if the HHTP request failed (status code != 200) so my code do not work with bad or empty data...
        xml_data = response.text
        
        # Parse XML
        root = ET.fromstring(xml_data)

        unique_alerts = []
        
        temp = {}
        for item in root.findall("./channel/item"):
            title = item.find("title").text.strip()
            link = item.find("link").text.strip()
            temp[title] = link
        
        unique_headlines_with_link = get_unique_disaster_list(temp)
        
        for headline in unique_headlines_with_link:
            # Fetch the CAP XML page
            cap_resp = requests.get(unique_headlines_with_link[headline])
            cap_resp.raise_for_status()
            cap_root = ET.fromstring(cap_resp.text)
            
            # # Namespaces used in CAP XML
            ns = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}

            # Extract event, headline, instruction, areaDesc, polygon, timestamp
            info = cap_root.find("cap:info", ns)
            if info is None:
                continue
            
            event = info.find("cap:event", ns).text.strip()
            headline = info.find("cap:headline", ns).text.strip()
            area_elem = info.find("cap:area/cap:areaDesc", ns)
            area_desc = area_elem.text.strip() if area_elem is not None else ""
            polygon_elem = info.find("cap:area/cap:polygon", ns)
            first_coord = extract_first_coordinate(polygon_elem.text if polygon_elem is not None else "")
            timestamp_elem = cap_root.find("cap:sent", ns)
            timestamp = timestamp_elem.text.strip() if timestamp_elem is not None else ""
            # Add to result
            unique_alerts.append({
                "title": headline,
                "link": link,
                "event": event,
                "timestamp": timestamp,
                "areas": area_desc,
                "first_coord": first_coord
            })

        dump_alerts_to_json(unique_alerts, filename="disaster_alerts.json")
        # Return as JSON
        return jsonify({"message": "JSON Updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
   

@disaster.route("/report_disaster", methods=["POST"])
def report_disaster():
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("Missing JSON body")
        
        required_fields = ["username", "phone", "latitude", "longitude", "disaster_type"]
        for field in required_fields:
            if field not in data or data[field] in [None, ""]:
                raise BadRequest(f"Missing required field: {field}")

        user = find_user(data["username"])    
        total_req = user["meta"]["total_requests_made"]
        active_req = user["meta"]["total_active_requests"]
        if active_req < 3:
            disaster_doc = user_disaster_model(data)
            write_request(disaster_doc)
            update_db("_id", user["_id"], "meta.total_active_requests", active_req+1)
            update_db("_id", user["_id"], "meta.total_requests_made", total_req+1)
            return jsonify({"message": f"The disaster request has been added with id {disaster_doc['_id']}"})
        else:
            return jsonify({"message": f"User has already three open requests, cancel one to make a new request"}), 429
    except Exception as e:
        return InternalServerError(f"Failed to register the disaster request: {e}")
    

@disaster.route("/confirm_help", methods=["POST"])
def confirm_help():
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("Missing JSON body")
        
        _id = data["_id"] # id of the disaster request...
        username = data["username"] # id of the helper...

        user = find_user(username)
        total_req_served = user["meta"]["total_requests_served"]

        add_responders(_id, [{"username": username, "phone": user["phone"], "email": user["email"]}])
        update_db("_id", user["_id"], "meta.total_requests_served", total_req_served+1)

        return jsonify({"message": f"{username} has been added in the list of responders for {_id} request"}), 200
    except Exception as e:
        return InternalServerError(f"Failed to register the disaster request: {e}")

@disaster.route("/mark_resolved", methods=["POST"])
def mark_resolved():
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("Missing JSON body")
        
        _id = data["_id"] # id of the disaster request...
        user = find_user(data["username"])
        active_req = user["meta"]["total_active_requests"]

        if active_req == 0:
            raise BadRequest(f"There is no active requests for this username {data['username']}")

        update_request(_id, ["is_resolved"], [True])
        update_db("_id", user["_id"], "meta.total_active_requests", active_req-1)
        return jsonify({"message": f"Request has been marked successful"}), 200
    except Exception as e:
        return InternalServerError(f"Failed to register the disaster request: {e}")

@disaster.route("/priortize/<string:_id>", methods=["GET"])
def priortize_request(_id):
    try:
        req = find_request("_id", _id)
        if req[0]:
            created_at = datetime.fromisoformat(req[0]["created_at"]).replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            time_diff = now - created_at
            if time_diff > timedelta(hours=0): ###
                update_request(req[0]["_id"], ["priority_count", "updated_at"], [req[0]["priority_count"] + 1, datetime.utcnow().isoformat()])
                return jsonify({"message": f"Your request has been prioritized"}), 200
            else:
                return jsonify({"message": f"Wait for 5 hrs before making another request"}), 200 # 5hrs
        else:
            return jsonify({"message": f"invalid request id {_id}"}), 400
    except Exception as e:
        return InternalServerError(f"Failed to register the disaster request: {e}")


@disaster.route("/cancel_request/<string:_id>", methods=["GET"])
def cancel_request(_id):
    try:
        req = find_request("_id", _id)
        user = find_user(req[0]["username"])
        active_req = user["meta"]["total_active_requests"]

        if not req:
            return jsonify({"message": f"Invalid request id: {_id}"}), 404

        if delete_request(req[0]["_id"]) == 1:
            update_db("_id", user["_id"], "meta.total_active_requests", active_req-1)
            return jsonify({"message": "Request has been cancelled."}), 200
        else:
            return jsonify({"message": f"invalid request id {_id}"}), 400
    except Exception as e:
        return InternalServerError(f"Failed to register the disaster request: {e}")
