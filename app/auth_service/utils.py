from werkzeug.security import check_password_hash
from werkzeug.exceptions import InternalServerError
from app.database import mongo
import random, hashlib, time
import requests
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
import os
import smtplib
from datetime import datetime
import requests

def read_db():
    try:
        docs = mongo.db.users.find({}, {"_id": 0})
        return docs
    except Exception as e:
        print(e)
        raise InternalServerError(description=f"Database read failed: {e}")

def write_db(user_doc: dict):
    try:
        mongo.db.users.insert_one(user_doc)
    except Exception as e:
        print(e)
        raise InternalServerError(description=f"Database write failed: {e}")

def validate_user(username: str, password: str):
    try:
        users = read_db()
        for user in users:
            if user['username'] == username and check_password_hash(user["password_hash"], password):
                return True
        return False
    except Exception as e:
        print(e)
        raise InternalServerError(description=f"Validation check failed: {e}")

def update_db(id_key: str, id_value, key_name: str, value):
    try:
        mongo.db.users.update_one(
            {id_key: id_value},
            {"$set": {key_name: value}}
        )
    except Exception as e:
        raise InternalServerError(description=f"Update failed: {e}")

def find_user(username: str):
    try:
        user = mongo.db.users.find_one({"username": username})
        return user
    except Exception as e:
        raise InternalServerError(description=f"User search failed: {e}")
    
def is_ngo_email(email: str) -> bool:
    base_dir = os.path.dirname(os.path.dirname(__file__))
    NGO_LIST = os.path.join(base_dir, "resources", "ngo_list.json")
    with open(NGO_LIST, "r") as f:
        NGO_LIST = json.load(f)
    domain = email.split("@")[-1].lower()
    return any(item["domain"].lower() == domain for item in NGO_LIST)

def generate_otp():
    otp = str(random.randint(100000, 999999))
    hashed = hashlib.sha256(otp.encode()).hexdigest()
    expiry = int(time.time()) + 300  # expires in 5 min
    return otp, hashed, expiry

def store_otp(username: str, hashed: str, expiry: int, mode: str):
    doc = {
        "username": username,
        "mode": mode,
        "hashed": hashed,
        "expiry": expiry
    }
    mongo.db.otp_data.insert_one(doc)

def check_otp(username: str, otp: str, mode: str):
    hashed_otp = hashlib.sha256(otp.encode()).hexdigest()

    doc = mongo.db.otp_data.find_one({
        "username": username,
        "mode": mode,
        "hashed": hashed_otp
    })

    if not doc:
        return False
    
    now = int(time.time())
    if now > doc["expiry"]:
        return False
    
    mongo.db.otp_data.delete_one({"_id": doc["_id"]})
    return True

def send_otp_email(to_email: str, otp: str):
    msg = MIMEMultipart("alternative")
    ts = time.time()
    readable = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    msg["Subject"] = f"Your OTP Code {readable}"
    msg["From"] = "worldofgumball0759@gmail.com"
    msg["To"] = to_email

    html = """\
    <html>
      <body style="font-family: Arial, sans-serif; color: #222;">
        <div style="background-color: #fff; padding: 20px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
            <h2 style="color:#2b6cb0; margin-top: 0;">Your Verification OTP</h2>
            <p>
                Your OTP code is: <strong>{{ otp }}</strong><br>
                This OTP will expire in {{ expiry_minutes }} minutes.
            </p>
        </div>
      </body>
    </html>
    """

    rendered_html = Template(html).render(otp=otp, expiry_minutes=5)
    msg.attach(MIMEText(rendered_html, "html"))

    # Send via Gmail SMTP
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login("worldofgumball0759@gmail.com", "eynnzjkxyovrsqub")
        server.send_message(msg)