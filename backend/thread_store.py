# thread_store.py -- used for multiple threads in a single telegram group

# asteroid_name -> telegram_message_id (anchor)
THREAD_ANCHORS = {}


def has_thread(supabase, asteroid_name: str) -> bool:
    res = supabase.table("threads") \
        .select("asteroid_name") \
        .eq("asteroid_name", asteroid_name) \
        .execute()
    return len(res.data) > 0

def save_thread_anchor(supabase, asteroid_name: str, message_id: int):
    supabase.table("threads").insert({
        "asteroid_name": asteroid_name,
        "telegram_message_id": message_id
    }).execute()

def get_anchor_for_asteroid(supabase, asteroid_name: str):
    res = supabase.table("threads") \
        .select("telegram_message_id") \
        .eq("asteroid_name", asteroid_name) \
        .single() \
        .execute()
    return res.data["telegram_message_id"] if res.data else None

def get_thread_by_anchor(supabase, message_id: int):
    res = supabase.table("threads") \
        .select("asteroid_name") \
        .eq("telegram_message_id", message_id) \
        .execute()
    return res.data[0]["asteroid_name"] if res.data else None
def delete_thread(supabase, asteroid_name: str) -> bool:
    res = supabase.table("threads") \
        .select("asteroid_name") \
        .eq("asteroid_name", asteroid_name) \
        .execute()

    if not res.data:
        return False

    supabase.table("threads") \
        .delete() \
        .eq("asteroid_name", asteroid_name) \
        .execute()

    return True

def list_threads(supabase):
    res = (
        supabase.table("threads")
        .select("asteroid_name, telegram_message_id, created_at")

        .order("created_at", desc=True)
        .execute()
    )

    return res.data or []
