from dotenv import load_dotenv
load_dotenv()   # MUST be before os.getenv

import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

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


if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or CHAT_ID in environment")
