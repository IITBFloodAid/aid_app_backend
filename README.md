The README uses AI assistance and is manually verified.

# IITB Flood Aid  -  Backend

Flask-powered REST API serving the IIT Bombay Flood Aid initiative. The backend orchestrates authentication, disaster request management, geospatial intelligence, LLM-driven assistance, and interactive flood risk mapping for field operators and affected communities.

---

## Feature Highlights

- **JWT-free session management**  -  user credentials are validated against MongoDB with secure password hashing; session state is maintained client-side.
- **NGO verification via OTP**  -  email-based one-time codes verify organizational affiliation against an approved domain list stored in `app/resources/ngo_list.json`.
- **Real-time disaster alerts**  -  fetches and parses CAP XML feeds from NDMA's SACHET service, deduplicates alerts using fuzzy matching, and sorts by proximity to user location.
- **Geospatial risk assessment**  -  combines OpenWeatherMap rainfall data, SRTM elevation datasets, and optional Base Flood Elevation (BFE) GeoJSON to compute flood risk levels and identify evacuation routes.
- **AI-powered chatbot**  -  integrates OpenRouter API with a disaster relief-focused system prompt, providing concise guidance on Indian NGOs and emergency resources.
- **User request limits**  -  enforces a maximum of 3 active disaster requests per user to prevent abuse while tracking resolution metrics.

## Stack

- [Flask](https://flask.palletsprojects.com/) with blueprint-based modular architecture
- [PyMongo](https://pymongo.readthedocs.io/) for MongoDB integration
- [Werkzeug](https://werkzeug.palletsprojects.com/) for password hashing and security utilities
- [Requests](https://requests.readthedocs.io/) for external API integration
- [Shapely](https://shapely.readthedocs.io/) + [rtree](https://rtree.readthedocs.io/) for geospatial operations
- [RapidFuzz](https://rapidfuzz.github.io/RapidFuzz/) for fuzzy string matching
- [OpenAI SDK](https://platform.openai.com/docs/api-reference) for LLM integration via OpenRouter

Python >= 3.8 is required; Python 3.10+ is recommended for optimal performance.

---

## Installation & Local Development

1. **Clone the repository**
   ```bash
   cd aid_app_backend
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   touch .env 
   ```
   Required environment variables:
   ```env
   MONGO_URI=mongodb://localhost:27017/aid_app  # or your MongoDB Atlas URI
   ```

5. **Start MongoDB**
   ```bash
   # If running locally:
   mongod --dbpath /path/to/data/directory
   
   # Or use MongoDB Atlas for cloud hosting
   ```

6. **Run the development server**
   ```bash
   python main.py
   ```
   The API will be available at `http://localhost:5000` with hot reloading enabled.

### Useful Commands

| Command | Description |
|---------|-------------|
| `python main.py` | Start the Flask development server |
| `python test.py` | Test LLM service integration |
| `pip freeze > requirements.txt` | Update dependencies list |

---

## API Services

### Authentication Service (`/auth`)
- `POST /auth/register` - Create new user account with email and password
- `POST /auth/login` - Authenticate user credentials
- `POST /auth/verification/send_otp` - Request OTP for email verification (supports NGO domain validation)
- `POST /auth/verification/verify_otp` - Validate OTP and mark user as verified

### Disaster Service (`/disaster`)
- `POST /disaster/get_data` - Fetch and filter NDMA disaster alerts by proximity
- `POST /disaster/report_disaster` - Submit new disaster assistance request
- `POST /disaster/confirm_help` - Register as responder for existing request
- `POST /disaster/mark_resolved` - Mark request as resolved
- `GET /disaster/priortize/<id>` - Increase priority of urgent request
- `GET /disaster/cancel_request/<id>` - Delete unresolved request

### Information Service (`/info`)
- `GET /info/get_requests/<username>` - Retrieve user's disaster requests (filtered by status)
- `POST /info/get_common_requests` - List all community requests sorted by proximity
- `GET /info/get_user_detail/<username>` - Fetch user profile information

### LLM Service (`/llm`)
- `POST /llm/get_llm_response` - Submit query to AI chatbot for disaster relief guidance

### Map Service (`/map`)
- `GET /map/display_map?lat=<lat>&lon=<lon>` - Generate interactive flood risk map with evacuation routes

---

## Data Models

### User Document (`users` collection)
```python
{
  "_id": "u_abc12345",
  "username": "john_doe",
  "password_hash": "hashed_password",
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+911234567890",
  "is_verified": False,
  "is_verified_ngo": False,
  "last_active_location": {"lat": 19.1234, "lon": 72.5678},
  "registered_at": "2025-11-26T10:00:00",
  "is_active": True,
  "roles": ["user"],
  "meta": {
    "profile_completed": True,
    "total_requests_made": 5,
    "total_requests_served": 3,
    "total_false_requests_made": 0,
    "total_active_requests": 2
  }
}
```

### Disaster Request Document (`disaster_requests` collection)
```python
{
  "_id": "uuid-string",
  "username": "john_doe",
  "phone": "+911234567890",
  "latitude": 19.1234,
  "longitude": 72.5678,
  "message": "Water entering ground floor",
  "disaster_type": "Flooding",
  "created_at": "2025-11-26T10:30:00",
  "is_resolved": False,
  "priority_count": 1,
  "priority_updated_at": "2025-11-26T10:30:00",
  "active_responders": [
    {"username": "helper1", "phone": "+919876543210", "email": "helper@example.com"}
  ]
}
```

---

## External API Integration

The backend integrates with multiple external services:

1. **NDMA SACHET** (`https://sachet.ndma.gov.in`) - Disaster alert RSS feed
2. **OpenWeatherMap** - Current weather and 5-day forecast data
3. **OpenTopoData** - SRTM90m elevation data
4. **Overpass API** - OpenStreetMap POI queries (hospitals, shelters, etc.)
5. **OSRM** - Routing service for evacuation path calculation
6. **OpenRouter** - LLM API gateway (uses Longcat Flash Chat model)


---

## Project Structure

```
app/
  __init__.py           # Flask app factory with CORS and blueprint registration
  config.py             # Secret key and token expiration settings
  database.py           # MongoDB connection initialization
  models.py             # User and disaster request document schemas
  
  auth_service/         # Authentication and verification
    routes.py           # Login, register, OTP endpoints
    utils.py            # Password hashing, OTP generation, email sending
  
  disaster_service/     # Disaster request management
    routes.py           # CRUD operations for disaster requests
    utils.py            # Geospatial utilities, alert processing
  
  info_service/         # Information retrieval
    routes.py           # User and community request queries
    utils.py            # Database query helpers
  
  llm_service/          # AI chatbot
    routes.py           # LLM query endpoint
    instructions.txt    # System prompt for disaster relief context
  
  map_service/          # Interactive flood mapping
    routes.py           # Map rendering endpoint
    utils.py            # Weather, elevation, BFE, routing utilities
    map_html.py         # Leaflet.js template
  
  resources/            # Static data files
    disaster_alerts.json  # Cached alerts
    ngo_list.json        # Approved NGO domains
```

---

## Security Considerations

- **Password Storage**: Uses Werkzeug's `generate_password_hash` with secure defaults
- **OTP Security**: SHA-256 hashed with 5-minute expiration window
- **Input Validation**: All endpoints validate required fields and data types
- **CORS**: Configured to allow cross-origin requests (can be restricted in production)

---

## Testing & QA Checklist

- Ensure MongoDB is running and accessible via `MONGO_URI`
- Test user registration with valid email format
- Verify OTP delivery and validation workflow
- Submit disaster requests and confirm geographic proximity sorting
- Check request limit enforcement (maximum 3 active requests)
- Test LLM chatbot with disaster-related queries
- Generate map visualization with various coordinates
- Confirm all external API integrations are functional

Manual testing via API client (Postman/curl) is recommended.

---

## Deployment

Example Gunicorn command:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 main:app
```
