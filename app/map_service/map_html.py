HTML = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Disaster & Safety Map — BFE-aware</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <style>
    html,body{height:100%;margin:0}
    #map{height:100vh;width:100vw}
    .poi-label { background: rgba(255,255,255,0.95); padding:4px 8px; border-radius:6px; font-weight:700; box-shadow:0 3px 8px rgba(0,0,0,0.12); white-space:nowrap; }
    .control-note{position:absolute;right:12px;top:12px;z-index:900;background:rgba(255,255,255,0.95);padding:10px;border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,0.12);max-width:320px;font-family:system-ui,Segoe UI,Roboto,Arial}
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="control-note">
    <div style="font-weight:800">Summary</div>
    <div style="margin-top:6px">Risk: <strong>{{ danger_level }}</strong></div>
    <div style="margin-top:6px">{{ danger_msg }}</div>
    <div style="margin-top:8px">Elevation: <strong>{{ elevation_display }}</strong></div>
    <div style="margin-top:4px">Rain(1h): <strong>{{ rain_label }}</strong></div>
    <div style="margin-top:4px">BFE data: <strong>{{ bfe_status }}</strong></div>
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const LAT = {{ lat }};
    const LON = {{ lon }};
    const OWM_KEY = {{ owm_api_key|tojson }};
    const POIS = {{ pois_json|safe }};
    const LOW_AREAS = {{ low_areas_json|safe }};
    const LOW_DISPLAY_RADIUS = {{ low_display_radius }};
    const DANGER_LEVEL = "{{ danger_level }}";
    const DANGER_MSG = "{{ danger_msg }}";
    const CIRCLE_RADIUS = {{ circle_radius }};
    const NEAREST_SHELTER = {{ nearest_shelter_json|safe }};
    const NEAREST_HIGH = {{ nearest_highground_json|safe }};
    const ROUTE_SHELTER = {{ route_to_shelter_json|safe }};
    const ROUTE_HIGH = {{ route_to_highground_json|safe }};
    const BFE_LOADED = {{ bfe_loaded }};

    const map = L.map('map').setView([LAT, LON], 14);
    const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19, attribution:'&copy; OpenStreetMap contributors'}).addTo(map);

    function owmTile(layer){ if(!OWM_KEY) return null; return L.tileLayer(`https://tile.openweathermap.org/map/${layer}/{z}/{x}/{y}.png?appid=${OWM_KEY}`, {maxZoom:19, attribution:'&copy; OpenWeatherMap'}); }
    const overlays = {};
    const precip = owmTile('precipitation_new'); if(precip) overlays["OWM Precipitation"] = precip;
    const clouds = owmTile('clouds_new'); if(clouds) overlays["OWM Clouds"] = clouds;
    L.control.layers({"OpenStreetMap": osm}, overlays, {collapsed:false}).addTo(map);

    // user marker (red)
    const user = L.circleMarker([LAT, LON], { radius:9, fillColor:'#d9534f', color:'#7a1d1d', weight:2, fillOpacity:0.95 }).addTo(map);
    user.bindPopup("<b>Your location</b>").openPopup();

    // danger circle
    const dangerColor = (DANGER_LEVEL==='high' ? '#d9534f' : (DANGER_LEVEL==='moderate' ? '#f0ad4e' : '#5cb85c'));
    const dangerCircle = L.circle([LAT, LON], { radius: CIRCLE_RADIUS || 1200, color: dangerColor, fillColor: dangerColor, fillOpacity:0.25 }).addTo(map);

    // POIs with permanent labels
    if(Array.isArray(POIS)){
      for(const p of POIS){
        try{
          const mk = L.marker([p.lat, p.lon]).addTo(map);
          const label = (p.name ? p.name : p.type) + " — " + Math.round((p.distance_m||0)) + " m";
          mk.bindTooltip(label, {permanent:true, direction:'top', offset:[0,-8], className:'poi-label'});
          mk.bindPopup(`<b>${p.name || p.type}</b><br/>Distance: ${Math.round(p.distance_m||0)} m`);
        }catch(e){ console.warn("poi render error", e, p); }
      }
    }

    // draw low-elevation areas (BFE-aware)
    if(Array.isArray(LOW_AREAS) && LOW_AREAS.length > 0){
      for(const a of LOW_AREAS){
        try{
          // color intensity could be adjusted by (bfe - elev) if available
          L.circle([a.lat, a.lon], {
            radius: LOW_DISPLAY_RADIUS,
            color: '#c82333',
            fillColor: '#f8d7da',
            fillOpacity: 0.55,
            weight: 1
          }).addTo(map).bindPopup(`<b>Low area</b><br/>Elev: ${a.elev} m${a.bfe !== undefined ? ('<br/>BFE: '+a.bfe+' m') : ''}`);
        }catch(e){ console.warn("low area draw error", e, a); }
      }
    }

    // Evacuation: shelter/high ground
    const evacGroup = L.featureGroup().addTo(map);
    evacGroup.addLayer(user);
    evacGroup.addLayer(dangerCircle);
    if(NEAREST_SHELTER){
      const s = NEAREST_SHELTER;
      const sm = L.marker([s.lat, s.lon], {title: s.name || 'Shelter'}).addTo(evacGroup);
      sm.bindPopup(`<b>Shelter</b><br/>${s.name || ''}<br/>Distance: ${Math.round(s.distance_m||0)} m`);
      if(ROUTE_SHELTER && ROUTE_SHELTER.geometry){ L.geoJSON(ROUTE_SHELTER, {style:{color:'#2a9df4',weight:4,opacity:0.9}}).addTo(evacGroup); }
      else { L.polyline([[LAT,LON],[s.lat,s.lon]], {color:'#2a9df4',weight:3,dashArray:'6 4'}).addTo(evacGroup); }
    }
    if(NEAREST_HIGH){
      const h = NEAREST_HIGH;
      const hm = L.circleMarker([h.lat, h.lon], { radius:7, color:'#207f2a', fillColor:'#2ecc71', fillOpacity:0.9 }).addTo(evacGroup);
      hm.bindPopup(`<b>Higher ground</b><br/>Elev: ${h.elevation_m || 'n/a'} m<br/>Distance: ${Math.round(h.distance_m||0)} m`);
      if(ROUTE_HIGH && ROUTE_HIGH.geometry){ L.geoJSON(ROUTE_HIGH, {style:{color:'#207f2a',weight:4,opacity:0.9}}).addTo(evacGroup); }
      else { L.polyline([[LAT,LON],[h.lat,h.lon]], {color:'#207f2a',weight:3,dashArray:'6 4'}).addTo(evacGroup); }
    }

    try { map.fitBounds(evacGroup.getBounds(), {padding:[40,40]}); } catch(e){ map.setView([LAT,LON], 14); }
  </script>
</body>
</html>
"""