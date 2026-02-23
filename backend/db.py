import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_supabase: Client = None

def get_supabase() -> Client:
    """Lazy initialization of Supabase client to support testing and local environments."""
    global _supabase
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if url and key:
            _supabase = create_client(url, key)
    return _supabase

def get_settings():
    """Retrieve settings for user 1. Create default if not exists."""
    client = get_supabase()
    if not client:
        return {}
    response = client.table("user_settings").select("*").eq("id", 1).execute()
    if not response.data:
        # Create default row if missing (Include all 6 PRD items)
        default_settings = {
            "id": 1,
            "weeks_ahead": 8,
            "selected_days": ["Fri", "Sat", "Sun"],
            "start_date": None,
            "end_date": None,
            "selected_types": ["특화야영장", "카라반", "자동차야영장"],
            "selected_parks": [],
            "cooldown_days": 3,
            "telegram_bot_token": "",
            "telegram_chat_id": ""
        }
        client.table("user_settings").insert(default_settings).execute()
        return default_settings
    return response.data[0]

def update_settings(settings):
    client = get_supabase()
    if not client:
        return
    # Upsert settings for user 1
    client.table("user_settings").upsert({"id": 1, **settings}).execute()

def check_cooldown(identifier, cooldown_days):
    client = get_supabase()
    if not client:
        return False
    # Check if this identifier was sent within the last N days
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=cooldown_days)
    response = client.table("notification_history") \
        .select("id") \
        .eq("identifier", identifier) \
        .gt("sent_at", cutoff.isoformat()) \
        .execute()
    return len(response.data) > 0

def record_notification(identifier):
    client = get_supabase()
    if not client:
        return
    from datetime import datetime, timezone
    client.table("notification_history").insert({
        "identifier": identifier,
        "sent_at": datetime.now(timezone.utc).isoformat()
    }).execute()
