import json
import logging
from flask import Flask, request, render_template_string
from app.map_service import map
from app.map_service.utils import fetch_current_weather, fetch_forecast,fetch_elevation_batch, radius_from_rain, find_nearby_pois, sample_low_elevation_areas_bfe,find_nearest_shelter, find_nearest_high_ground, route_osrm, assess_simple
from app.map_service.utils import OPENWEATHERMAP_API_KEY, SHELTER_SEARCH_RADIUS, LOW_AREA_DISPLAY_RADIUS, _BFE_FEATURES, BFE_GEOJSON_PATH, POI_SEARCH_RADIUS
from app.map_service.map_html import HTML

@map.route("/display_map", methods=["GET"])
def index():
    lat_s = request.args.get("lat", "").strip()
    lon_s = request.args.get("lon", "").strip()
    if not lat_s or not lon_s:
        return ("Provide coordinates via query params: /?lat=<lat>&lon=<lon>", 400)
    try:
        lat = float(lat_s); lon = float(lon_s)
    except ValueError:
        return ("Invalid coordinates.", 400)

    current = fetch_current_weather(lat, lon)
    forecast = fetch_forecast(lat, lon)

    elev_list = fetch_elevation_batch([(lat, lon)])
    elevation = elev_list[0] if elev_list else None

    danger_level, reasons, rain_val = assess_simple(current, forecast, elevation)
    danger_msg = "; ".join(reasons) if reasons else "No immediate issues detected by simple heuristics."
    circle_radius = radius_from_rain(rain_val)
    rain_label = f"{round(rain_val,2)} mm" if rain_val is not None else "no data"
    elevation_display = f"{round(elevation,2)} m" if elevation is not None else "unknown"

    pois = find_nearby_pois(lat, lon, radius=POI_SEARCH_RADIUS)
    pois_for_js = [{"lat":p["lat"], "lon":p["lon"], "distance_m":p["distance_m"], "name":p.get("name"), "type":p.get("type")} for p in (pois or [])[:30]]

    low_areas = sample_low_elevation_areas_bfe(lat, lon)


    nearest_shelter = None; nearest_high = None; route_to_shelter = None; route_to_high = None; show_evac=False
    if danger_level == "high":
        show_evac = True
        nearest_shelter = find_nearest_shelter(lat, lon, radius=SHELTER_SEARCH_RADIUS)
        nearest_high = find_nearest_high_ground(lat, lon, elevation)
        if nearest_shelter:
            route_to_shelter = route_osrm(lat, lon, nearest_shelter["lat"], nearest_shelter["lon"])
        if nearest_high:
            route_to_high = route_osrm(lat, lon, nearest_high["lat"], nearest_high["lon"])

    pois_json = json.dumps(pois_for_js)
    nearest_shelter_json = json.dumps(nearest_shelter) if nearest_shelter else "null"
    nearest_highground_json = json.dumps(nearest_high) if nearest_high else "null"
    route_to_shelter_json = json.dumps(route_to_shelter) if route_to_shelter else "null"
    route_to_highground_json = json.dumps(route_to_high) if route_to_high else "null"
    low_areas_json = json.dumps(low_areas)

    html_template = """PUT_YOUR_HTML_TEMPLATE_HERE"""  
    tpl = globals().get("HTML") or html_template

    return render_template_string(tpl,
                                  lat=lat, lon=lon,
                                  owm_api_key=OPENWEATHERMAP_API_KEY,
                                  pois_json=pois_json,
                                  low_areas_json=low_areas_json,
                                  low_display_radius=LOW_AREA_DISPLAY_RADIUS,
                                  danger_level=danger_level,
                                  danger_msg=danger_msg,
                                  circle_radius=circle_radius,
                                  nearest_shelter_json=nearest_shelter_json,
                                  nearest_highground_json=nearest_highground_json,
                                  route_to_shelter_json=route_to_shelter_json,
                                  route_to_highground_json=route_to_highground_json,
                                  elevation_display=elevation_display,
                                  rain_label=rain_label,
                                  bfe_loaded=(1 if len(_BFE_FEATURES)>0 else 0))


