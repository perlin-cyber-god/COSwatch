# telegram_updates.py -- to take into account the inflow of messages (continuos updates)
from thread_store import get_thread_by_anchor
from message_store import add_message


def handle_update(update, supabase):
    msg = update.get("message")
    if not msg:
        return

    text = msg.get("text", "")
    user = msg["from"].get("username", "unknown")

    if "reply_to_message" in msg:
        anchor_id = msg["reply_to_message"]["message_id"]
        asteroid = get_thread_by_anchor(supabase, anchor_id)

        if asteroid:
            add_message(supabase, asteroid, user, text)
            print(f"[THREAD:{asteroid}] {user}: {text}")
            return

    print(f"[GENERAL] {user}: {text}")

    # General chat
    print(f"[GENERAL] {user}: {text}")
    if msg["chat"]["type"] == "private":
        telegram_id = msg["chat"]["id"]
        username = msg["from"].get("username")

        # store telegram_id against your user_id

