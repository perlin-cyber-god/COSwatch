#this file acts as context for the telegram bot and also to manage threads

from thread_store import has_thread, save_thread_anchor
from telegram_client import send_message

def create_asteroid_thread(asteroid_name: str, supabase, context: dict | None = None) -> bool:
    if has_thread(supabase, asteroid_name):
        return False

    text = f"🧵 THREAD STARTED\n🛰️ Asteroid: {asteroid_name}\n"

    if context:
        text += (
            f"\n📏 Diameter: {context['diameter']} m"
            f"\n💨 Velocity: {context['velocity']} km/h"
            f"\n📍 Miss Distance: {context['miss_distance']} km"
            f"\n⚠️ Risk Score: {context['risk_score']}"
        )

    text += "\n\nReply to this message to discuss."

    result = send_message(text)
    message_id = result["result"]["message_id"]

    save_thread_anchor(supabase, asteroid_name, message_id)
    return True
