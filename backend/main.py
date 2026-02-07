from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import date, timedelta
from supabase import create_client
import os
from dotenv import load_dotenv

# ---- LOCAL IMPORTS ----
from telegram_client import send_message, get_updates
from telegram_updates import handle_update
from asteroid_context import create_asteroid_thread
from message_store import get_messages
from thread_store import delete_thread
from message_store import delete_messages
from thread_store import list_threads
import threading
import time

# ---------------- LOAD ENV ----------------
load_dotenv()
AUTO_THREAD_RISK_THRESHOLD = 25

# ---------------- CONFIG ----------------
NASA_API_KEY = os.getenv("NASA_API_KEY")
NASA_BASE_URL = "https://api.nasa.gov/neo/rest/v1"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("❌ Supabase credentials missing")

# ---------------- SUPABASE ----------------
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- APP ----------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- TELEGRAM STATE ----------------
last_update_id = None


# ---------------- STARTUP ----------------
@app.on_event("startup")
def startup_notice():
    send_message("COSwatch backend online. Science imminent.")


# ---------------- THREAD CREATION ----------------
@app.post("/debug/create-thread/{asteroid_name}")
def create_thread(asteroid_name: str):
    created = create_asteroid_thread(asteroid_name, supabase)

    if created:
        return {"status": "thread created"}
    return {"status": "thread already exists"}


# ---------------- USER INIT ----------------
@app.post("/user/init")
def init_user(user_id: str):
    res = (
        supabase.table("community_members")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )

    if not res.data:
        supabase.table("community_members").insert({
            "user_id": user_id,
            "status": "pending",
            "role": "researcher"
        }).execute()
        return {"tier": "researcher"}

    record = res.data[0]

    if record["role"] == "admin":
        return {"tier": "admin"}

    if record["status"] == "approved":
        return {"tier": "community"}

    return {"tier": "researcher"}


# ---------------- GET USER TIER ----------------
@app.get("/user/tier/{user_id}")
def get_user_tier(user_id: str):
    res = (
        supabase.table("community_members")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )

    if not res.data:
        return {"tier": "researcher"}

    record = res.data[0]

    if record["role"] == "admin":
        return {"tier": "admin"}

    if record["status"] == "approved":
        return {"tier": "community"}

    return {"tier": "researcher"}


# ---------------- ADMIN APPROVAL ----------------
@app.post("/community/approve")
def approve_user(admin_id: str, target_user_id: str):
    res = (
        supabase.table("community_members")
        .select("*")
        .eq("user_id", admin_id)
        .execute()
    )

    if not res.data or res.data[0]["role"] != "admin":
        return {"error": "Not authorized"}

    supabase.table("community_members") \
        .update({"status": "approved"}) \
        .eq("user_id", target_user_id) \
        .execute()

    return {"message": "User approved"}


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
    except Exception:
        return 0


# ---------------- ROOT ----------------
@app.get("/")
def root():
    return {"status": "Cosmic Watch Backend Running"}


# ---------------- NEO FEED ----------------
@app.get("/neo/feed")
def get_neo_feed():
    today = date.today()
    end = today + timedelta(days=1)

    url = (
        f"{NASA_BASE_URL}/feed"
        f"?start_date={today}"
        f"&end_date={end}"
        f"&api_key={NASA_API_KEY}"
    )

    res = requests.get(url)

    if res.status_code != 200:
        return {
            "error": "NASA API request failed",
            "status_code": res.status_code,
            "response": res.text
        }

    data = res.json()
    result = []

    for day in data.get("near_earth_objects", {}):
        for neo in data["near_earth_objects"][day]:
            try:
                approach = neo["close_approach_data"][0]
                velocity = approach["relative_velocity"]["kilometers_per_hour"]
                distance = approach["miss_distance"]["kilometers"]
            except Exception:
                velocity = "N/A"
                distance = "N/A"

            risk = risk_score(neo)

            # 🔥 AUTO-CREATE THREAD BASED ON RISK
            if risk >= AUTO_THREAD_RISK_THRESHOLD:
                create_asteroid_thread(
                    neo["name"],
                    supabase,
                    context={
                        "diameter": round(
                            neo["estimated_diameter"]["meters"]["estimated_diameter_max"], 1
                        ),
                        "velocity": round(float(velocity), 1),
                        "miss_distance": round(float(distance), 1),
                        "risk_score": risk
        }
    )


            result.append({
                "id": neo["id"],
                "name": neo["name"],
                "hazardous": neo["is_potentially_hazardous_asteroid"],
                "velocity_kph": velocity,
                "miss_distance_km": distance,
                "risk_score": risk
            })

    return result

# ---------------- THREAD MESSAGE INSPECTION ----------------
@app.get("/debug/thread-messages/{asteroid_name}")
def debug_thread_messages(asteroid_name: str):
    return {
        "asteroid": asteroid_name,
        "messages": get_messages(supabase, asteroid_name)
    }


# ---------------- TELEGRAM POLLING ----------------
@app.post("/debug/poll-telegram")
def poll_telegram():
    global last_update_id

    updates = get_updates(last_update_id)

    for u in updates:
        handle_update(u, supabase)
        last_update_id = u["update_id"] + 1

    return {"processed": len(updates)}


#----asteroid subscription

@app.post("/asteroid/track")
def track_asteroid(user_id: str, asteroid_name: str):
    # check user is approved
    res = supabase.table("community_members") \
        .select("status") \
        .eq("user_id", user_id) \
        .execute()

    if not res.data or res.data[0]["status"] != "approved":
        return {"error": "User not approved"}

    # avoid duplicates
    existing = supabase.table("asteroid_subscriptions") \
        .select("id") \
        .eq("user_id", user_id) \
        .eq("asteroid_name", asteroid_name) \
        .execute()

    if existing.data:
        return {"status": "already tracking"}

    supabase.table("asteroid_subscriptions").insert({
        "user_id": user_id,
        "asteroid_name": asteroid_name
    }).execute()

    return {"status": "tracking started"}


# debug endpoint for dm alerts 
@app.post("/debug/alert/{asteroid_name}")
def alert_users(asteroid_name: str):
    subs = supabase.table("asteroid_subscriptions") \
        .select("user_id") \
        .eq("asteroid_name", asteroid_name) \
        .execute()

    if not subs.data:
        return {"sent": 0}

    sent = 0

    for row in subs.data:
        user_id = row["user_id"]

        # map your user_id → telegram chat_id
        # (for demo, assume user_id IS chat_id)
        try:
            send_dm(
                int(user_id),
                f"🚨 Alert for asteroid {asteroid_name}\nNew update detected."
            )
            sent += 1
        except Exception as e:
            print("DM failed:", e)

    return {"sent": sent}

#delete threads
@app.delete("/thread/{asteroid_name}")
def delete_thread_endpoint(asteroid_name: str):
    deleted = delete_thread(supabase, asteroid_name)

    if not deleted:
        return {"status": "thread not found"}

    delete_messages(supabase, asteroid_name)

    return {"status": "thread deleted"}

#list current threads
@app.get("/threads")
def get_threads():
    threads = list_threads(supabase)

    return {
        "threads": threads
    }

#auto sync data and threads 
AUTO_SYNC_INTERVAL = 60  # seconds

def auto_sync():
    while True:
        try:
            print("[AUTO-SYNC] Fetching NASA feed...")
            get_neo_feed()
        except Exception as e:
            print("[AUTO-SYNC ERROR]", e)
        time.sleep(AUTO_SYNC_INTERVAL)

@app.on_event("startup")
def start_auto_sync():
    t = threading.Thread(target=auto_sync, daemon=True)
    t.start()
