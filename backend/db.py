import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

def get_settings():
    """Retrieve settings for user 1. Create default if not exists."""
    if not supabase:
        return {}
    response = supabase.table("user_settings").select("*").eq("id", 1).execute()
    if not response.data:
        # Create default row if missing
        default_settings = {
            "id": 1,
            "weeks_ahead": 8,
            "selected_days": ["Fri", "Sat", "Sun"],
            "selected_types": ["특화야영장", "카라반", "자동차야영장"],
            "selected_parks": [],
            "cooldown_days": 3
        }
        supabase.table("user_settings").insert(default_settings).execute()
        return default_settings
    return response.data[0]

def update_settings(settings):
    if not supabase:
        return
    # Upsert settings for user 1
    supabase.table("user_settings").upsert({"id": 1, **settings}).execute()

def check_cooldown(identifier, cooldown_days):
    if not supabase:
        return False
    # Check if this identifier was sent within the last N days
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=cooldown_days)
    response = supabase.table("notification_history") \
        .select("id") \
        .eq("identifier", identifier) \
        .gt("sent_at", cutoff.isoformat()) \
        .execute()
    return len(response.data) > 0

def record_notification(identifier):
    if not supabase:
        return
    supabase.table("notification_history").insert({"identifier": identifier}).execute()
