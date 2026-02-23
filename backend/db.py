import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

def get_settings():
    if not supabase:
        return {}
    response = supabase.table("user_settings").select("*").eq("id", 1).execute()
    return response.data[0] if response.data else {}

def update_settings(settings):
    if not supabase:
        return
    # Convert lists if necessary
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
