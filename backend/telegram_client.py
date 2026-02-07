from dotenv import load_dotenv
load_dotenv()

import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or CHAT_ID in environment")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(text: str):
    r = requests.post(
        f"{BASE_URL}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": text
        }
    )
    r.raise_for_status()
    return r.json()

def get_updates(offset=None):
    params = {"timeout": 10}
    if offset:
        params["offset"] = offset

    r = requests.get(f"{BASE_URL}/getUpdates", params=params)
    r.raise_for_status()
    return r.json()["result"]

def send_dm(chat_id: int, text: str):
    r = requests.post(
        f"{BASE_URL}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text
        }
    )
    r.raise_for_status()
