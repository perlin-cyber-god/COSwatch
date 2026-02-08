# telegram_updates.py
from telegram_dm_bot import send_dm, ACTIVE_CHAT_IDS

def handle_update(update):
    msg = update.get("message")
    if not msg:
        return

    text = msg.get("text", "")
    chat_id = msg["chat"]["id"]

    # register chat
    ACTIVE_CHAT_IDS.add(chat_id)

    if text == "/start":
        send_dm(
            chat_id,
            "👋 COSwatch online.\n\nYou will receive asteroid alerts here."
        )