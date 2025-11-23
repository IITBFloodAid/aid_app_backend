import os
import json
import math
import logging
from flask import Flask, request, render_template_string
import requests
from shapely.geometry import shape, Point
from shapely.prepared import prep
try:
    from rtree import index as rtree_index
    RTREE_AVAILABLE = True
except Exception:
    RTREE_AVAILABLE = False
    
    
    
OPENWEATHERMAP_API_KEY = "32113c867d091c412946491c5d2671cd"
OPENTOPODATA_URL = "https://api.opentopodata.org/v1/srtm90m"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSRM_ROUTE_TEMPLATE = "http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
OWM_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

POI_SEARCH_RADIUS = 8000
SHELTER_SEARCH_RADIUS = 10000
HIGH_GROUND_MAX_RADIUS = 15000

LOW_ELEVATION_THRESHOLD_M = 135.0
LOW_AREA_SAMPLE_RADII = [500, 1000, 1500, 2000, 2500, 3000]
LOW_AREA_SAMPLE_ANGLES = 12
LOW_AREA_DISPLAY_RADIUS = 300

HIGH_RAIN_THRESHOLD = 10.0
MED_RAIN_THRESHOLD = 5.0

BFE_SAFETY_MARGIN_M = 0.0
BFE_GEOJSON_PATH = os.getenv("BFE_GEOJSON_PATH", "bfe.geojson")

# ---------- Utilities ----------
def haversine_meters(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1 = math.radians(lat1); phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1); dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# -------- BFE support (loader + query) --------
_BFE_FEATURES = []
_RTREE_IDX = None

def load_bfe_geojson(path=BFE_GEOJSON_PATH):
    global _BFE_FEATURES, _RTREE_IDX
    _BFE_FEATURES = []
    _RTREE_IDX = None
    if not os.path.isfile(path):
        # app.logger.info("No BFE geojson found at %s — skipping BFE loading.", path)
        return 0
    try:
        with open(path, "r", encoding="utf-8") as fh:
            gj = json.load(fh)
    except Exception as e:
        # app.logger.warning("Failed to read BFE geojson: %s", e)
        return 0
    features = gj.get("features", []) if isinstance(gj, dict) else []
    if RTREE_AVAILABLE and features:
        _RTREE_IDX = rtree_index.Index()
    for feat in features:
        props = feat.get("properties", {}) or {}
        bfe_val = None
        if "BFE" in props: bfe_val = props["BFE"]
        elif "bfe" in props: bfe_val = props["bfe"]
        else:
            for k, v in props.items():
                if isinstance(v, (int, float)):
                    kl = k.lower()
                    if any(x in kl for x in ("bfe", "base", "flood", "elev")):
                        bfe_val = v
                        break
        if bfe_val is None:
            continue
        geom_json = feat.get("geometry")
        if not geom_json:
            continue
        try:
            geom = shape(geom_json)
        except Exception:
            continue
        if geom.is_empty:
            continue
        prepared = prep(geom)
        centroid = (geom.centroid.y, geom.centroid.x)
        idx = len(_BFE_FEATURES)
        _BFE_FEATURES.append({"geom": geom, "prep": prepared, "bfe": float(bfe_val), "centroid": centroid})
        if _RTREE_IDX is not None:
            minx, miny, maxx, maxy = geom.bounds
            _RTREE_IDX.insert(idx, (minx, miny, maxx, maxy))
    # app.logger.info("Loaded %d BFE features from %s", len(_BFE_FEATURES), path)
    return len(_BFE_FEATURES)

def get_bfe_for_point(lat, lon, nearest_fallback=True):
    if not _BFE_FEATURES:
        return None
    pt = Point(lon, lat)
    candidates = range(len(_BFE_FEATURES))
    if _RTREE_IDX is not None:
        try:
            candidates = list(_RTREE_IDX.intersection((lon, lat, lon, lat)))
        except Exception:
            candidates = range(len(_BFE_FEATURES))
    for i in candidates:
        feat = _BFE_FEATURES[i]
        try:
            if feat["prep"].contains(pt):
                return feat["bfe"]
        except Exception:
            continue
    for feat in _BFE_FEATURES:
        try:
            if feat["prep"].contains(pt):
                return feat["bfe"]
        except Exception:
            continue
    if not nearest_fallback:
        return None
    best = None
    for feat in _BFE_FEATURES:
        clat, clon = feat["centroid"]
        d = haversine_meters(lat, lon, clat, clon)
        if best is None or d < best[0]:
            best = (d, feat)
    if best:
        return best[1]["bfe"]
    return None

# load BFE at startup (if exists)
bfe_count = load_bfe_geojson(BFE_GEOJSON_PATH)

# ---------- Elevation (batch) ----------
def fetch_elevation_batch(locations):
    if not locations:
        return []
    try:
        locs_str = "|".join(f"{lat},{lon}" for lat,lon in locations)
        r = requests.get(OPENTOPODATA_URL, params={"locations": locs_str}, timeout=12)
        r.raise_for_status()
        j = r.json()
        res = []
        for it in j.get("results", []):
            e = it.get("elevation")
            res.append(float(e) if e is not None else None)
        if len(res) < len(locations):
            res += [None] * (len(locations) - len(res))
        return res
    except Exception as e:
        # app.logger.warning("OpenTopoData batch failed: %s", e)
        return [None] * len(locations)

# ---------- POI lookup ----------
def find_nearby_pois(lat, lon, radius=POI_SEARCH_RADIUS):
    q = f"""
    [out:json][timeout:25];
    (
      node(around:{radius},{lat},{lon})["amenity"~"hospital|police|fire_station|shelter|community_centre|school"];
      way(around:{radius},{lat},{lon})["amenity"~"hospital|police|fire_station|shelter|community_centre|school"];
      relation(around:{radius},{lat},{lon})["amenity"~"hospital|police|fire_station|shelter|community_centre|school"];
    );
    out center 50;
    """
    try:
        r = requests.post(OVERPASS_URL, data=q.encode('utf-8'), timeout=25)
        r.raise_for_status()
        data = r.json()
        elems = data.get("elements", [])
        pois = []
        for el in elems:
            if el.get("type") == "node":
                elat = el.get("lat"); elon = el.get("lon")
            else:
                center = el.get("center")
                if not center:
                    continue
                elat = center.get("lat"); elon = center.get("lon")
            tags = el.get("tags", {})
            name = tags.get("name")
            amen = tags.get("amenity") or tags.get("emergency") or tags.get("building")
            dist = haversine_meters(lat, lon, elat, elon)
            pois.append({"lat": elat, "lon": elon, "distance_m": dist, "name": name, "type": amen, "tags": tags})
        pois.sort(key=lambda x: x["distance_m"])
        return pois[:30]
    except Exception as e:
        # app.logger.warning("overpass POI failed: %s", e)
        return []

# ---------- NEW: find_nearest_shelter (uses POIs) ----------
def find_nearest_shelter(lat, lon, radius=SHELTER_SEARCH_RADIUS):
    """
    Return the best nearby shelter-like POI or None.
    Preference order: shelter -> community_centre -> school -> place_of_worship -> hospital -> police -> fire_station
    """
    pois = find_nearby_pois(lat, lon, radius=radius)
    if not pois:
        return None
    priority = {
        "shelter": 0,
        "community_centre": 1,
        "school": 2,
        "place_of_worship": 3,
        "hospital": 4,
        "police": 5,
        "fire_station": 6
    }
    best = None
    for p in pois:
        t = (p.get("type") or "").lower()
        pr = priority.get(t, 99)
        if best is None:
            best = (pr, p)
        else:
            if pr < best[0] or (pr == best[0] and p["distance_m"] < best[1]["distance_m"]):
                best = (pr, p)
    return best[1] if best else pois[0]

# ---------- High ground finder (samples concentric rings) ----------
def find_nearest_high_ground(lat, lon, base_elev):
    if base_elev is None:
        base_elev = 0.0
    target = max(base_elev + 8.0, 16.0)
    angles = [i * (360.0 / LOW_AREA_SAMPLE_ANGLES) for i in range(LOW_AREA_SAMPLE_ANGLES)]
    step = 1000
    maxr = HIGH_GROUND_MAX_RADIUS
    for radius in range(step, maxr+1, step):
        ring = []
        for angle_deg in angles:
            angle = math.radians(angle_deg)
            R = 6378137.0
            lat1 = math.radians(lat); lon1 = math.radians(lon)
            lat2 = math.asin(math.sin(lat1)*math.cos(radius/R) + math.cos(lat1)*math.sin(radius/R)*math.cos(angle))
            lon2 = lon1 + math.atan2(math.sin(angle)*math.sin(radius/R)*math.cos(lat1), math.cos(radius/R)-math.sin(lat1)*math.sin(lat2))
            lat2d = math.degrees(lat2); lon2d = math.degrees(lon2)
            ring.append((lat2d, lon2d))
        elevs = fetch_elevation_batch(ring)
        for idx, e in enumerate(elevs):
            if e is not None and e >= target:
                found_lat, found_lon = ring[idx]
                dist = haversine_meters(lat, lon, found_lat, found_lon)
                return {"lat": found_lat, "lon": found_lon, "elevation_m": round(e,2), "distance_m": dist}
    return None

# ---------- OSRM routing ----------
def route_osrm(lat1, lon1, lat2, lon2):
    try:
        url = OSRM_ROUTE_TEMPLATE.format(lat1=lat1, lon1=lon1, lat2=lat2, lon2=lon2)
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        j = r.json()
        if j.get("code") == "Ok" and j.get("routes"):
            geom = j["routes"][0].get("geometry")
            return {"type":"Feature","geometry":geom,"properties":{"distance":j["routes"][0].get("distance"),"duration":j["routes"][0].get("duration")}}
    except Exception as e:
        no_idea = 5
        # app.logger.warning("osrm route failed: %s", e)
    return None

# ---------- Low-elevation sampling using BFE when available ----------
def sample_low_elevation_areas_bfe(lat, lon, radii=LOW_AREA_SAMPLE_RADII, angles_count=LOW_AREA_SAMPLE_ANGLES, safety_margin_m=BFE_SAFETY_MARGIN_M):
    pts = []
    meta = []
    for r in radii:
        for i in range(angles_count):
            angle = 2 * math.pi * (i / angles_count)
            R = 6378137.0
            lat1 = math.radians(lat); lon1 = math.radians(lon)
            lat2 = math.asin(math.sin(lat1)*math.cos(r/R) + math.cos(lat1)*math.sin(r/R)*math.cos(angle))
            lon2 = lon1 + math.atan2(math.sin(angle)*math.sin(r/R)*math.cos(lat1), math.cos(r/R)-math.sin(lat1)*math.sin(lat2))
            lat2d = math.degrees(lat2); lon2d = math.degrees(lon2)
            pts.append((lat2d, lon2d))
            meta.append({"r": r, "angle_deg": int(math.degrees(angle))})
    if not pts:
        return []
    elevs = fetch_elevation_batch(pts)
    low_points = []
    for (pt, m, e) in zip(pts, meta, elevs):
        if e is None:
            continue
        bfe = get_bfe_for_point(pt[0], pt[1], nearest_fallback=True)
        if bfe is not None:
            is_low = (e <= (bfe + safety_margin_m))
        else:
            is_low = (e <= LOW_ELEVATION_THRESHOLD_M)
        if is_low:
            low_points.append({"lat": pt[0], "lon": pt[1], "elev": round(e,2), "bfe": round(bfe,2) if bfe is not None else None, "meta": m})
    return low_points

# ---------- Small risk helpers ----------
def fetch_current_weather(lat, lon):
    try:
        r = requests.get(OWM_CURRENT_URL, params={"lat": lat, "lon": lon, "appid": OPENWEATHERMAP_API_KEY, "units": "metric"}, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        # app.logger.warning("OWM current failed: %s", e)
        return None

def fetch_forecast(lat, lon):
    try:
        r = requests.get(OWM_FORECAST_URL, params={"lat": lat, "lon": lon, "appid": OPENWEATHERMAP_API_KEY, "units": "metric"}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        # app.logger.warning("OWM forecast failed: %s", e)
        return None

def assess_simple(current, forecast, elevation):
    rain = None
    if current and "rain" in current:
        rain = current["rain"].get("1h") or current["rain"].get("3h")
    rain_val = rain or 0.0
    overall = "low"
    reasons = []
    if rain_val >= HIGH_RAIN_THRESHOLD and elevation is not None and elevation <= 5.0:
        overall = "high"; reasons.append("heavy rain + low elevation")
    elif rain_val >= MED_RAIN_THRESHOLD and elevation is not None and elevation <= 15.0:
        overall = "moderate"; reasons.append("moderate rain + low elevation")
    else:
        if rain_val >= HIGH_RAIN_THRESHOLD:
            overall = "moderate"; reasons.append("heavy rain but elevation not very low")
    return overall, reasons, rain_val

def radius_from_rain(rain_mm):
    MIN_RADIUS = 1000; MAX_RADIUS = 20000
    try:
        rv = max(0.0, min(rain_mm if rain_mm is not None else 0.0, 30.0))
        return int(MIN_RADIUS + (MAX_RADIUS - MIN_RADIUS) * (rv / 30.0))
    except:
        return MIN_RADIUS