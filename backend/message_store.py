# message_store.py -- takes into account incoming messages

from collections import defaultdict
MAX_MESSAGES = 100

def add_message(supabase, asteroid_name: str, user: str, text: str):
    supabase.table("thread_messages").insert({
        "asteroid_name": asteroid_name,
        "username": user,
        "message": text
    }).execute()

    res = supabase.table("thread_messages") \
        .select("id") \
        .eq("asteroid_name", asteroid_name) \
        .order("created_at", desc=True) \
        .execute()

    if len(res.data) > MAX_MESSAGES:
        excess = res.data[MAX_MESSAGES:]
        ids = [m["id"] for m in excess]

        supabase.table("thread_messages") \
            .delete() \
            .in_("id", ids) \
            .execute()

def get_messages(supabase, asteroid_name: str):
    res = supabase.table("thread_messages") \
        .select("username,message,created_at") \
        .eq("asteroid_name", asteroid_name) \
        .order("created_at") \
        .execute()
    return res.data
def delete_messages(supabase, asteroid_name: str):
    supabase.table("messages") \
        .delete() \
        .eq("asteroid_name", asteroid_name) \
        .execute()
