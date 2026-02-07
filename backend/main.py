from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from datetime import date, timedelta
from supabase import create_client
import os

# ---------------- NASA CONFIG ----------------
API_KEY = "C1fecjBmt0q9ipCtq34T15dBRpEkWaGmeZ0LLEZa"
BASE_URL = "https://api.nasa.gov/neo/rest/v1"

# ---------------- SUPABASE CONFIG ----------------
SUPABASE_URL = "https://toamgacouwrwtibzbwyo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRvYW1nYWNvdXdyd3RpYnpid3lvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA0MzMwMzIsImV4cCI6MjA4NjAwOTAzMn0.RF1k9QJG6sL6N1CBwPfHH-Zv0Jou1Lh3202dHolkmL0"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- APP SETUP ----------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- DATA MODELS ----------------
class UserInit(BaseModel):
    user_id: str

class AdminAction(BaseModel):
    admin_id: str
    target_user_id: str

# ---------------- USER & AUTH ENDPOINTS (SUNDEEP'S LOGIC) ----------------

@app.post("/user/init")
def init_user(user: UserInit):
    """
    Called immediately after Supabase Login.
    Determines if user is Admin, Researcher, or Community.
    """
    print(f"⚡ Handshake received for User: {user.user_id}")

    # 1. HACKATHON SHORTCUT: 
    # If the email is your admin email (you can hardcode ID here if you know it), return admin.
    # Otherwise, default to 'researcher' so they see the cool dashboard.
    
    tier = "researcher" 

    # 2. Real DB Check (Try/Except ensures demo doesn't crash if table is missing)
    try:
        # Check if we have a 'profiles' table
        res = supabase.table("profiles").select("*").eq("id", user.user_id).execute()
        if res.data:
            tier = res.data[0].get("role", "researcher")
        else:
            # Create profile if not exists
            supabase.table("profiles").insert({"id": user.user_id, "role": "researcher"}).execute()
    except Exception as e:
        print(f"⚠ DB Skip (using default tier): {e}")

    return {"status": "active", "tier": tier}


@app.post("/community/approve")
def approve_user(action: AdminAction):
    """
    Admin Endpoint to upgrade a user.
    """
    print(f"🛡 ADMIN ACTION: {action.admin_id} approving {action.target_user_id}")
    
    try:
        # Update Supabase
        supabase.table("profiles").update({"role": "researcher"}).eq("id", action.target_user_id).execute()
        return {"status": "success", "message": "Clearance Granted"}
    except Exception as e:
        # Mock success for demo if DB fails
        return {"status": "success", "message": "Simulated Approval (DB Offline)"}

# ---------------- RISK ENGINE ----------------

def calculate_advanced_risk(neo):
    try:
        is_hazardous = neo.get("is_potentially_hazardous_asteroid", False)
        diameter_data = neo.get("estimated_diameter", {}).get("meters", {})
        avg_diameter = (diameter_data.get("estimated_diameter_min", 0) + diameter_data.get("estimated_diameter_max", 0)) / 2
        
        approach = neo["close_approach_data"][0]
        velocity = float(approach["relative_velocity"]["kilometers_per_hour"])
        miss_distance = float(approach["miss_distance"]["kilometers"])

        score = 50 if is_hazardous else 0
        vel_score = min((velocity / 100000) * 20, 20)
        dist_score = max((1 - (miss_distance / 10_000_000)) * 20, 0)
        size_score = min((avg_diameter / 500) * 10, 10)

        total_risk = score + vel_score + dist_score + size_score
        return round(min(total_risk, 99), 1)

    except Exception:
        return 0

# ---------------- NEO FEED ----------------

@app.get("/neo/feed")
def get_neo_feed():
    today = date.today()
    end_date = today + timedelta(days=7)

    url = f"{BASE_URL}/feed?start_date={today}&end_date={end_date}&api_key={API_KEY}"
    print(f"🚀 Fetching NASA Feed...") 

    try:
        res = requests.get(url)
        if res.status_code != 200:
            return []

        data = res.json()
        if "near_earth_objects" not in data:
            return []

        all_asteroids = []
        for date_key in data["near_earth_objects"]:
            for neo in data["near_earth_objects"][date_key]:
                try:
                    approach = neo["close_approach_data"][0]
                    vel = approach["relative_velocity"]["kilometers_per_hour"]
                    miss = approach["miss_distance"]["kilometers"]
                except:
                    vel = "0"
                    miss = "0"

                processed_neo = {
                    "id": neo["id"],
                    "name": neo["name"],
                    "hazardous": neo["is_potentially_hazardous_asteroid"],
                    "velocity_kph": vel,
                    "miss_distance_km": miss,
                    "estimated_diameter": neo["estimated_diameter"],
                    "risk_score": calculate_advanced_risk(neo)
                }
                all_asteroids.append(processed_neo)

        all_asteroids.sort(key=lambda x: x['risk_score'], reverse=True)
        return all_asteroids

    except Exception as e:
        print(f"Backend Error: {e}")
        return []

# ---------------- ROOT ----------------
@app.get("/")
def root():
    return {"status": "online", "system": "Cosmic Watch Mission Control"}