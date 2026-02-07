#this is the main backend, apart from fetching data  , this also controlls user sessions

from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import date, timedelta
from supabase import create_client

# ---------------- NASA CONFIG ----------------
API_KEY = "MfXTgtAvf7g9qCg3ukNH7zxf1wq4CePTSBQi4AUD"
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

# ---------------- WATCHLIST ENDPOINTS ----------------

@app.post("/watchlist/{asteroid_id}")
def add_to_watchlist(asteroid_id: str, authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    user = supabase.auth.get_user(token)

    user_id = user.user.id

    data = supabase.table("watchlist").insert({
        "user_id": user_id,
        "asteroid_id": asteroid_id
    }).execute()

    return data.data


@app.get("/watchlist")
def get_watchlist(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    user = supabase.auth.get_user(token)

    user_id = user.user.id

    data = (
        supabase.table("watchlist")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )

    return data.data

# ---------------- RISK ENGINE ----------------

def risk_score(neo):
    try:
        diameter = neo["estimated_diameter"]["meters"]["estimated_diameter_max"]
        hazardous = neo["is_potentially_hazardous_asteroid"]
        miss = float(
            neo["close_approach_data"][0]["miss_distance"]["kilometers"]
        )

        score = 0
        if hazardous:
            score += 50
        score += min(diameter / 10, 30)
        score += max(0, 20 - (miss / 1_000_000))

        return round(score, 2)
    except:
        return 0

# ---------------- ROOT ----------------

@app.get("/")
def root():
    return {"message": "Cosmic Watch Backend Running"}

# ---------------- NEO FEED ----------------

@app.get("/neo/feed")
def get_neo_feed():
    today = date.today()
    end = today + timedelta(days=1)

    url = (
        f"{BASE_URL}/feed"
        f"?start_date={today}"
        f"&end_date={end}"
        f"&api_key={API_KEY}"
    )

    res = requests.get(url)

    if res.status_code != 200:
        return {
            "error": "NASA API request failed",
            "status_code": res.status_code,
            "response": res.text
        }

    data = res.json()

    if "near_earth_objects" not in data:
        return {
            "error": "Unexpected NASA response",
            "response": data
        }

    result = []

    for day in data["near_earth_objects"]:
        for neo in data["near_earth_objects"][day]:
            try:
                approach = neo["close_approach_data"][0]
                velocity = approach["relative_velocity"]["kilometers_per_hour"]
                distance = approach["miss_distance"]["kilometers"]
            except:
                velocity = "N/A"
                distance = "N/A"

            result.append({
                "id": neo["id"],
                "name": neo["name"],
                "hazardous": neo["is_potentially_hazardous_asteroid"],
                "velocity_kph": velocity,
                "miss_distance_km": distance,
                "risk_score": risk_score(neo)
            })

    return result