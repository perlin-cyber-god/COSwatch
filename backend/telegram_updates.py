# telegram_updates.py -- to take into account the inflow of messages (continuos updates)
from thread_store import get_thread_by_anchor
from message_store import add_message
from dm_state import ACTIVE_DM_CHAT_ID


def handle_update(update, supabase):
    global ACTIVE_DM_CHAT_ID

    msg = update.get("message")
    if not msg:
        return

    text = msg.get("text", "")
    user = msg["from"].get("username", "unknown")
    chat = msg.get("chat", {})
    chat_type = chat.get("type")

    # 1️⃣ Handle /start in private DM → enable alerts
    if chat_type == "private" and text == "/start":
        ACTIVE_DM_CHAT_ID = chat["id"]
        print("[DM ENABLED] chat_id =", ACTIVE_DM_CHAT_ID)
        return

    # 2️⃣ Handle replies to thread anchors
    if "reply_to_message" in msg:
        anchor_id = msg["reply_to_message"]["message_id"]
        asteroid = get_thread_by_anchor(supabase, anchor_id)

        if asteroid:
            add_message(supabase, asteroid, user, text)
            print(f"[THREAD:{asteroid}] {user}: {text}")
            return

    # 3️⃣ Everything else = general chat
    print(f"[GENERAL] {user}: {text}")
