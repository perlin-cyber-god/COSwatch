# telegram_dm_bot.py
import requests
import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

ACTIVE_CHAT_IDS = set()

def send_dm(chat_id: int, text: str):
    requests.post(
        f"{API}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )

def poll_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset

    res = requests.get(f"{API}/getUpdates", params=params)
    return res.json().get("result", [])
