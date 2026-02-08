# fake_chat_store.py

from collections import defaultdict
from datetime import datetime

THREAD_MESSAGES = defaultdict(list)

def get_messages(thread_id: str):
    return THREAD_MESSAGES[thread_id]

def add_message(thread_id: str, user: str, text: str):
    THREAD_MESSAGES[thread_id].append({
        "user": user,
        "text": text,
        "created_at": datetime.utcnow().isoformat()
    })
