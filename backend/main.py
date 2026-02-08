from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import date, timedelta
from supabase import create_client
import os
from dotenv import load_dotenv
import threading
import time

# ---- LOCAL IMPORTS ----
# Ensure these files exist in your backend folder!
from telegram_client import send_message, get_updates, send_dm
from telegram_updates import handle_update
from asteroid_context import create_asteroid_thread
from message_store import get_messages, delete_messages
from thread_store import delete_thread, list_threads

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
    try:
        send_message("COSwatch backend online. Science imminent.")
    except Exception as e:
        print(f"⚠️ Telegram Startup Warning: {e}")

# ---------------- AUTO SYNC ----------------
AUTO_SYNC_INTERVAL = 60  # seconds

def auto_sync():
    """Background task to fetch NASA data and sync Telegram periodically"""
    while True:
        try:
            print("[AUTO-SYNC] 🔄 Syncing NASA Feed & Telegram...")
            # Trigger feed update (which auto-creates threads)
            get_neo_feed()
            
            # Also poll telegram messages
            global last_update_id
            updates = get_updates(last_update_id)
            if updates:
                for u in updates:
                    handle_update(u, supabase)
                    last_update_id = u["update_id"] + 1
                print(f"[AUTO-SYNC] Processed {len(updates)} telegram updates")
                
        except Exception as e:
            print(f"[AUTO-SYNC ERROR] {e}")
        
        time.sleep(AUTO_SYNC_INTERVAL)

@app.on_event("startup")
def start_auto_sync():
    t = threading.Thread(target=auto_sync, daemon=True)
    t.start()


# ---------------- THREAD CREATION ----------------
@app.post("/debug/create-thread/{asteroid_name}")
def create_thread(asteroid_name: str):
    try:
        created = create_asteroid_thread(asteroid_name, supabase)
        if created:
            return {"status": "thread created"}
        return {"status": "thread already exists"}
    except Exception as e:
        return {"status": "error", "details": str(e)}


# ---------------- USER INIT ----------------
@app.post("/user/init")
def init_user(payload: dict):
    # Expects {"user_id": "..."}
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")

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
        return {"tier": "researcher", "status": "pending"}

    record = res.data[0]

    # Return structure matching frontend expectation
    return {
        "tier": record["role"], 
        "status": record["status"]
    }


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
    return {"tier": record["role"]}


# ---------------- ADMIN APPROVAL ----------------
@app.post("/community/approve")
def approve_user(payload: dict):
    # Expects {"admin_id": "...", "target_user_id": "..."}
    admin_id = payload.get("admin_id")
    target_user_id = payload.get("target_user_id")

    res = (
        supabase.table("community_members")
        .select("*")
        .eq("user_id", admin_id)
        .execute()
    )

    if not res.data or res.data[0]["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    supabase.table("community_members") \
        .update({"status": "approved", "role": "community"}) \
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
            "status_code": res.status_code
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
                velocity = "0"
                distance = "0"

            risk = risk_score(neo)
            
            # Standardize numeric values for frontend
            try:
                vel_float = float(velocity)
                dist_float = float(distance)
                diam_float = neo["estimated_diameter"]["meters"]["estimated_diameter_max"]
            except:
                vel_float = 0.0
                dist_float = 0.0
                diam_float = 0.0

            # 🔥 AUTO-CREATE THREAD BASED ON RISK
            if risk >= AUTO_THREAD_RISK_THRESHOLD:
                try:
                    create_asteroid_thread(
                        neo["name"],
                        supabase,
                        context={
                            "diameter": round(diam_float, 1),
                            "velocity": round(vel_float, 1),
                            "miss_distance": round(dist_float, 1),
                            "risk_score": risk
                        }
                    )
                except Exception as e:
                    print(f"Failed to create thread for {neo['name']}: {e}")

            result.append({
                "id": neo["id"],
                "name": neo["name"],
                "hazardous": neo["is_potentially_hazardous_asteroid"],
                "velocity_kph": vel_float,
                "miss_distance_km": dist_float,
                "risk_score": risk,
                "estimated_diameter": diam_float
            })

    # Sort by risk (High to Low)
    result.sort(key=lambda x: x['risk_score'], reverse=True)
    return result

# ---------------- THREAD MESSAGE INSPECTION ----------------
@app.get("/debug/thread-messages/{asteroid_name}")
def debug_thread_messages(asteroid_name: str):
    return {
        "asteroid": asteroid_name,
        "messages": get_messages(supabase, asteroid_name)
    }


# ---------------- TELEGRAM POLLING (Manual Trigger) ----------------
@app.post("/debug/poll-telegram")
def poll_telegram():
    global last_update_id
    try:
        updates = get_updates(last_update_id)
        processed = 0
        if updates:
            for u in updates:
                handle_update(u, supabase)
                last_update_id = u["update_id"] + 1
                processed += 1
        return {"processed": processed}
    except Exception as e:
        return {"error": str(e)}


# ---------------- ASTEROID SUBSCRIPTION ----------------
@app.post("/asteroid/track")
def track_asteroid(payload: dict):
    # Expects {"user_id": "...", "asteroid_name": "..."}
    user_id = payload.get("user_id")
    asteroid_name = payload.get("asteroid_name")

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


# ---------------- DELETE THREADS ----------------
@app.delete("/thread/{asteroid_name}")
def delete_thread_endpoint(asteroid_name: str):
    deleted = delete_thread(supabase, asteroid_name)

    if not deleted:
        return {"status": "thread not found"}

    delete_messages(supabase, asteroid_name)
    return {"status": "thread deleted"}

# ---------------- LIST THREADS ----------------
@app.get("/threads")
def get_threads():
    threads = list_threads(supabase)
    return {"threads": threads}