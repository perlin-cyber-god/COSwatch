from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import date, timedelta
import os
import threading
import time
from dotenv import load_dotenv
from supabase import create_client

# ---------- LOCAL IMPORTS ----------
from telegram_client import send_message, send_dm, get_updates
from telegram_updates import handle_update
from asteroid_context import create_asteroid_thread
from thread_store import delete_thread, list_threads
from message_store import get_messages, delete_messages
from dm_state import ACTIVE_DM_CHAT_ID

# ---------- ENV ----------
load_dotenv()

NASA_API_KEY = os.getenv("NASA_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not NASA_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing environment variables")

# ---------- CONSTANTS ----------
NASA_BASE_URL = "https://api.nasa.gov/neo/rest/v1"
AUTO_THREAD_RISK_THRESHOLD = 25
AUTO_SYNC_INTERVAL = 60  # seconds

# ---------- STATE ----------
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()
last_update_id = None
previous_risk_map = {}

# ---------- MIDDLEWARE ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- STARTUP ----------
@app.on_event("startup")
def startup():
    send_message("COSwatch backend online. Science imminent.")
    threading.Thread(target=auto_sync, daemon=True).start()
    threading.Thread(target=periodic_check, daemon=True).start()


# ---------- RISK ENGINE ----------
def risk_score(neo):
    try:
        diameter = neo["estimated_diameter"]["meters"]["estimated_diameter_max"]
        hazardous = neo["is_potentially_hazardous_asteroid"]
        miss = float(neo["close_approach_data"][0]["miss_distance"]["kilometers"])

        score = 0
        if hazardous:
            score += 50
        score += min(diameter / 10, 30)
        score += max(0, 20 - (miss / 1_000_000))
        return round(score, 2)
    except Exception:
        return 0


# ---------- ROUTES ----------
@app.get("/")
def root():
    return {"status": "Cosmic Watch Backend Running"}


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
    res.raise_for_status()
    data = res.json()

    result = []

    for day in data.get("near_earth_objects", {}):
        for neo in data["near_earth_objects"][day]:
            try:
                approach = neo["close_approach_data"][0]
                velocity = float(approach["relative_velocity"]["kilometers_per_hour"])
                distance = float(approach["miss_distance"]["kilometers"])
            except Exception:
                velocity = 0
                distance = 0

            risk = risk_score(neo)

            if risk >= AUTO_THREAD_RISK_THRESHOLD:
                create_asteroid_thread(
                    neo["name"],
                    supabase,
                    context={
                        "risk_score": risk,
                        "velocity": round(velocity, 1),
                        "miss_distance": round(distance, 1),
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


@app.post("/debug/poll-telegram")
def poll_telegram():
    global last_update_id

    updates = get_updates(last_update_id)
    for u in updates:
        handle_update(u, supabase)
        last_update_id = u["update_id"] + 1

    return {"processed": len(updates)}


@app.get("/debug/thread-messages/{asteroid_name}")
def debug_thread_messages(asteroid_name: str):
    return {
        "asteroid": asteroid_name,
        "messages": get_messages(supabase, asteroid_name)
    }


@app.delete("/thread/{asteroid_name}")
def delete_thread_endpoint(asteroid_name: str):
    if not delete_thread(supabase, asteroid_name):
        return {"status": "thread not found"}

    delete_messages(supabase, asteroid_name)
    return {"status": "thread deleted"}


@app.get("/threads")
def get_threads():
    return {"threads": list_threads(supabase)}


# ---------- AUTO SYNC ----------
def auto_sync():
    while True:
        try:
            print("[AUTO-SYNC] Fetching NASA feed…")
            get_neo_feed()
        except Exception as e:
            print("[AUTO-SYNC ERROR]", e)
        time.sleep(AUTO_SYNC_INTERVAL)


# ---------- ROGUE DETECTION ----------
def detect_rogue_asteroids(current_data):
    global previous_risk_map
    deltas = []

    for neo in current_data:
        name = neo["name"]
        risk = neo["risk_score"]
        old = previous_risk_map.get(name, 0)
        delta = risk - old

        if delta > 0:
            deltas.append({
                "name": name,
                "risk": risk,
                "delta": round(delta, 2)
            })

        previous_risk_map[name] = risk

    deltas.sort(key=lambda x: x["delta"], reverse=True)
    return deltas[:4]


def send_rogue_dm(message: str):
    if ACTIVE_DM_CHAT_ID is None:
        print("[DM SKIPPED] No active user")
        return
    send_dm(ACTIVE_DM_CHAT_ID, message)


def periodic_check():
    while True:
        try:
            data = get_neo_feed()
            top = detect_rogue_asteroids(data)

            if top:
                msg = "🚨 Asteroid Risk Update\n\n" + "\n".join(
                    f"{i+1}. {x['name']} | Risk {x['risk']} (+{x['delta']})"
                    for i, x in enumerate(top)
                )
                send_rogue_dm(msg)

        except Exception as e:
            print("[AUTO CHECK ERROR]", e)

        time.sleep(AUTO_SYNC_INTERVAL)

#chat 


@app.post("/thread/{asteroid_name}/message")
def post_thread_message(asteroid_name: str, payload: dict):
    user = payload.get("user", "web")
    text = payload.get("text")

    if not text:
        return {"error": "empty"}

    # store message
    add_message(supabase, asteroid_name, user, text)

    # OPTIONAL: also forward to Telegram thread
    send_message(f"[WEB] {user}: {text}")

    return {"status": "ok"}
