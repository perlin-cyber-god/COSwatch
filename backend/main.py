from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import date, timedelta
import threading
import time
import os
from dotenv import load_dotenv

from fake_chat_store import get_messages, add_message
from telegram_dm_bot import poll_updates, send_dm, ACTIVE_CHAT_IDS
from telegram_updates import handle_update


# ================= ENV =================
load_dotenv()

NASA_API_KEY = os.getenv("NASA_API_KEY")
if not NASA_API_KEY:
    raise RuntimeError("Missing NASA_API_KEY")

NASA_BASE_URL = "https://api.nasa.gov/neo/rest/v1"

AUTO_SYNC_INTERVAL = 60  # seconds
RISK_ALERT_THRESHOLD = 40

last_update_id = None
previous_risk_map = {}

app = FastAPI()


# ================= CORS =================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://0.0.0.0:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================= STARTUP =================
@app.on_event("startup")
def startup():
    print("[STARTUP] COSwatch backend online")
    threading.Thread(target=auto_sync, daemon=True).start()
    threading.Thread(target=periodic_check, daemon=True).start()


# ================= UTILS =================
def risk_score(neo: dict) -> float:
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
        return 0.0


def notify_users(message: str):
    for chat_id in ACTIVE_CHAT_IDS:
        send_dm(chat_id, message)


# ================= ROUTES =================
@app.get("/")
def root():
    return {"status": "Cosmic Watch Backend Running"}


# ---- frontend login handshake ----
@app.post("/user/init")
def init_user(_: dict):
    return {"tier": "guest"}


# ---- NEO FEED ----
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

    output = []

    for day in data.get("near_earth_objects", {}):
        for neo in data["near_earth_objects"][day]:
            try:
                approach = neo["close_approach_data"][0]
                velocity = float(
                    approach["relative_velocity"]["kilometers_per_hour"]
                )
                distance = float(
                    approach["miss_distance"]["kilometers"]
                )
                diameter = round(
                    neo["estimated_diameter"]["meters"]["estimated_diameter_max"], 1
                )
            except Exception:
                velocity = 0.0
                distance = 0.0
                diameter = 10.0

            risk = risk_score(neo)

            output.append({
                "id": neo["id"],                  # thread id
                "name": neo["name"],
                "hazardous": neo["is_potentially_hazardous_asteroid"],
                "velocity_kph": velocity,
                "miss_distance_km": distance,
                "risk_score": risk,
                "size_m": diameter,               # REQUIRED by frontend
            })

    return output


# ================= FAKE CHAT =================
@app.get("/thread/{thread_id}")
def get_thread(thread_id: str):
    return {
        "thread_id": thread_id,
        "messages": get_messages(thread_id),
    }


@app.post("/thread/{thread_id}/message")
def post_thread_message(thread_id: str, payload: dict):
    text = payload.get("text")
    user = payload.get("user", "guest")

    if not text:
        return {"error": "empty message"}

    add_message(thread_id, user, text)
    return {"status": "ok"}


# ================= AUTO SYNC =================
def auto_sync():
    while True:
        try:
            print("[AUTO-SYNC] Fetching NASA feed")
            get_neo_feed()
        except Exception as e:
            print("[AUTO-SYNC ERROR]", e)
        time.sleep(AUTO_SYNC_INTERVAL)


# ================= RISK MONITOR =================
def detect_rogue_asteroids(data):
    global previous_risk_map
    deltas = []

    for neo in data:
        tid = neo["id"]
        risk = neo["risk_score"]
        old = previous_risk_map.get(tid, 0)
        delta = risk - old

        if delta > 0 and risk >= RISK_ALERT_THRESHOLD:
            deltas.append({
                "id": tid,
                "name": neo["name"],
                "risk": risk,
                "delta": round(delta, 2),
            })

        previous_risk_map[tid] = risk

    return deltas


def periodic_check():
    while True:
        try:
            data = get_neo_feed()
            alerts = detect_rogue_asteroids(data)

            for a in alerts:
                notify_users(
                    f"🚨 Asteroid Alert\n\n"
                    f"{a['name']}\n"
                    f"Risk: {a['risk']} (+{a['delta']})"
                )

        except Exception as e:
            print("[AUTO CHECK ERROR]", e)

        time.sleep(AUTO_SYNC_INTERVAL)


# ================= TELEGRAM =================
@app.post("/debug/poll-telegram")
def poll_telegram():
    global last_update_id

    updates = poll_updates(last_update_id)

    for u in updates:
        handle_update(u)
        last_update_id = u["update_id"] + 1

    return {"processed": len(updates)}
