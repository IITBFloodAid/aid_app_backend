#### Note: Will send the following in case of internal server error:
- Response format: 
	 ```
	 {
	   "message": "Something went wrong :(, please try again."
	 } 500
	 ```

### `auth/register`
* Request format:
```
{
  "username": "john_doe",
  "password": "123",
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+911234567890",
  "location": {"lat": 12.9716, "lon": 77.5946} # this to be sent from the frontend
}
```
* Response format:
```
{
	"message": "Registration successful",
	"username": "john_doe",
	"verified": false,
	"email": "john@example.com"
}
```

### `auth/login`
* Request format:
```
{
  "username": "john_doe",
  "password": "123",
  "location": {"lat": 12.9716, "lon": 77.5946} # this to be sent from the frontend
}
```
* Response format:
```
{
	"message": "Login successful",
	"username": "john_doe",
	"verified": false
}
```

### `auth/verification/send_otp
* Has query parameter ngo, if given with ngo=1 will check if your email id is from the list of approved mail
 Request format:
 ```
	{
		"username": "john_doe"
	} 
```
-  Response format:
	```
	{
		"message": "OTP on a3141b@gmail.com has been sent, please enter in next 5 minutes"/ "Sorry, your email is not from an approved NGO domain. Please contact the administrators if you believe your domain should be added to the accepted list"
	}, 200 / 400
	```
### `auth/verification/verify_otp_ngo`
- Request format:
 ```
	{
		"username": "john_doe"
		"otp": "1234"
	} 
```
-  Response format:
	```
	{
		"message": "Your profile has been marked under verified NGO."
	}, 200 / 401
	```

### `info/get_requests/<string:username> 
* This is a get request
- query param, opened = 1 then give open requests
- Response format (sorted priority-wise):
	 ```
	 [
		 {
		  "username": "john_doe",
		  "phone": "+911234567890",
		  "message": "Flood water entering my street.",
		  "disaster_type": "Flood",
		  "created_at": "2025-11-16T20:13:49.641451",
		  "priority_count": 1,
		  "priority_updated_at": "2025-11-16T20:13:49.641464+00:00",   
		  "active_responders": []
		}
	 ], 200
	 ``` 
- Will send 400 if the request is bad.

### `info/get_common_requests
- This gives all the requests of all the users that are opened.
- Request format:
	 ```
	 {
		  "username": "om_dhamani",
		  "latitude": 89,
		  "longitude": 80
	 }
	 ```
- Response format(sorted according to proximity from the user's location);
   ```
   [
    {
        "username": "john_doe",
        "phone": "+911234567890",
        "latitude": 13.0951,
        "longitude": 80.2017,
        "message": "Transformer producing loud sparks.",
        "disaster_type": "Electrical Hazard",
        "created_at": "2025-11-16T20:14:31.261804",
        "priority_updated_at": "2025-11-16T20:14:31.261822+00:00",
        "active_responders": [],
        "distance": 8440.240479344726
    },
    {
        "username": "john_doe",
        "phone": "+911234567890",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "message": "Flood water entering my street.",
        "disaster_type": "Flood",
        "created_at": "2025-11-16T20:13:49.641451",
        "priority_updated_at": "2025-11-16T20:13:49.641464+00:00",
        "active_responders": [],
        "distance": 8441.619850773042
    }
], 200
   ```
- Will send 400 if the request is bad.

### `info/get_user_detail/<string:username>:
 - Response format:
	```
	   {
		   "username": "abh_3141",
		   "name": "Abhay",
		   "email": "a3141b@gmail.com",
		   "phone": "+917876755273",
		   "is_verified": false,
		   "is_verified_ngo": true,
		   "last_active_location": {"lat": null, "lon": null},
		   "registered_at": "2025-11-22T14:11:50.970238",
		   "is_active": true,
		   "meta": {
			   "profile_completed": true,
			   "total_requests_made": 0,
			   "total_requests_served": 0,
			   "total_false_requests_made": 0,
			   "total_active_requests": 0
			   }
		}
	 }, 200
	```

### `disaster-service/report_disaster`
(cap of three active requests)
* Request format:
	```
	{
  "username": "john_doe",
  "phone": "+911234567890",
  "latitude": 13.0827,
  "longitude": 80.2707,
  "message": "Water level rising near my house, need assistance.",
  "disaster_type": "Flood"
  }

	```
* Response format:
	```
	{
	  "message": "The disaster request has been added with id 123"
	} 200
	```
### `disaster-service/confirm_help` (completed)
- Request format:
	 ```
		{
			"_id": "1234" # id of the request...
			"username": "om_dhamani", # username of the helper
		}
	 ```
- Response format:
```
	{
	  "message": "User has been added in the list of responders for this request"
	} 200
```

### `disaster-service/mark_resolved` (completed)
- Request format:
```
{
	"_id": "1234"
	"username": "om_dhamani"
}
```
- Response format:
```
{
	"message": "Request has been marked successful."
} 200
```

### `disaster-service/priortize/<_id>` (completed)
- Response format:
```
{
	"message": "Request has been priortized." / "Please wait at least 5 hours from creation or last prioritization before prioritizing this request."
} 200, 403
```

### `disaster-service/cancel_request/<_id>` (completed)
- Response format:
```
{
	"message": "Request has been cancelled."
} 200
```
### `disaster-service/get_data` (completed)
- Request format:
```
{
	"username": "om_dhamani",
	"latitude": 89,
	"longitude": 80
}
```
- Response format (will give sorted from the user's location):
```
{
	{
		"Headline": "flood at Prof om's house",
		"Timestamp": "2025-11-08T13:01:30Z,
		"Area Descriptioin": "powai, mumbai"
	}
} 200
```
llm/get_llm_response
Request:
{
	"message": "i am in flood what to do?"
}

Response:
{
	"message": "Move to higher ground immediately. Avoid walking or driving through floodwater. Turn off electricity and gas. Contact Disaster Management Helpline: 1078 or 112 (emergency). For aid, reach All India Disaster Mitigation Institute (aidmi.org) or Rapid Response (rapidresponse.org.in, helpline: 1800 120 44004).Stay tuned to local weather updates via IMD (mausam.imd.gov.in). Use dry clothes, boil water, and avoid contaminated food. For medical help, dial 108 (ambulance). NGOs like Goonj (goonj.org) and Hindrise (hindrise.org) distribute relief kits—register online or via helpline."
}