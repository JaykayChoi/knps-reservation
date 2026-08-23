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

def get_settings(setting_id=None):
    """Retrieve settings. If setting_id is None, returns all active settings."""
    client = get_supabase()
    if not client:
        return {} if setting_id else []
    
    if setting_id:
        response = client.table("user_settings").select("*").eq("id", setting_id).execute()
        if not response.data:
            return {}
        return response.data[0]
    else:
        # For backward compatibility, if is_active column doesn't exist, return all settings
        try:
            response = client.table("user_settings").select("*").eq("is_active", True).order("created_at").execute()
            return response.data
        except Exception as e:
            # If column doesn't exist, return all settings
            if "is_active" in str(e):
                response = client.table("user_settings").select("*").order("id").execute()
                return response.data
            raise

def get_all_settings():
    """Retrieve all settings including inactive ones."""
    client = get_supabase()
    if not client:
        return []
    try:
        response = client.table("user_settings").select("*").order("created_at").execute()
        return response.data
    except Exception as e:
        # If created_at column doesn't exist, order by id
        if "created_at" in str(e):
            response = client.table("user_settings").select("*").order("id").execute()
            return response.data
        raise

def create_settings(settings):
    """Create a new settings row."""
    client = get_supabase()
    if not client:
        return None
    # Get existing settings to check count and find next ID
    response = client.table("user_settings").select("id").execute()
    existing_settings = response.data
    # Check if we already have 10 settings (max limit)
    if len(existing_settings) >= 10:
        raise ValueError("Maximum of 10 settings reached")
    # Calculate next available ID
    if existing_settings:
        next_id = max(setting["id"] for setting in existing_settings) + 1
    else:
        next_id = 1  # Start from 1 if no settings exist
    
    # Set default values
    default_settings = {
        "weeks_ahead": 8,
        "selected_days": ["Fri", "Sat", "Sun"],
        "start_date": None,
        "end_date": None,
        "selected_types": ["특화야영장", "카라반", "자동차야영장"],
        "selected_parks": [],
        "selected_parkinglots": [],
        "cooldown_days": 3,
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "include_waiting": True
    }
    
    # Only add new columns if they exist in schema
    extra_fields = {
        "name": "New Settings",
        "date_mode": "weekday",
        "is_active": True,
        "include_waiting": True
    }
    # Merge with provided settings
    merged_settings = {**default_settings, **settings}
    # Try to add extra fields, but they might fail if columns don't exist
    for key, value in extra_fields.items():
        if key not in merged_settings:
            merged_settings[key] = value
    
    # Add the calculated ID to the settings
    merged_settings["id"] = next_id
    
    try:
        response = client.table("user_settings").insert(merged_settings).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        error_str = str(e)
        if any(col in error_str for col in ["name", "date_mode", "is_active", "include_waiting", "selected_parkinglots", "created_at", "updated_at"]):
            for col in ["name", "date_mode", "is_active", "include_waiting", "selected_parkinglots", "created_at", "updated_at"]:
                merged_settings.pop(col, None)
            response = client.table("user_settings").insert(merged_settings).execute()
            if response.data:
                return response.data[0]
        raise
def update_settings(settings, setting_id=None):
    client = get_supabase()
    if not client:
        return
    # If setting_id is provided, update specific setting
    if setting_id:
        client.table("user_settings").update(settings).eq("id", setting_id).execute()
    else:
        # For backward compatibility, update first active setting or first setting
        try:
            response = client.table("user_settings").select("id").eq("is_active", True).order("created_at").limit(1).execute()
            if response.data:
                client.table("user_settings").update(settings).eq("id", response.data[0]["id"]).execute()
        except Exception as e:
            # If is_active column doesn't exist, update first setting
            if "is_active" in str(e):
                response = client.table("user_settings").select("id").order("id").limit(1).execute()
                if response.data:
                    client.table("user_settings").update(settings).eq("id", response.data[0]["id"]).execute()
            else:
                raise

def check_cooldown(setting_id, target_date, park_name, facility_type, is_waiting, cooldown_days):
    # A zero-day cooldown means every matching availability may notify again.
    # Return before initializing Supabase so the notification history cannot
    # suppress alerts in this mode.
    if cooldown_days <= 0:
        return False

    client = get_supabase()
    if not client:
        return False
    
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=cooldown_days)
    
    query = client.table("notification_history") \
        .select("id") \
        .eq("setting_id", setting_id) \
        .eq("target_date", target_date) \
        .eq("park_name", park_name) \
        .eq("facility_type", facility_type) \
        .eq("is_waiting", is_waiting) \
        .gt("sent_at", cutoff.isoformat())
    
    response = query.execute()
    return len(response.data) > 0

def record_notification(setting_id, target_date, park_name, facility_type, is_waiting):
    client = get_supabase()
    if not client:
        return
    from datetime import datetime, timezone
    data = {
        "setting_id": setting_id,
        "target_date": target_date,
        "park_name": park_name,
        "facility_type": facility_type,
        "is_waiting": is_waiting,
        "sent_at": datetime.now(timezone.utc).isoformat()
    }
    client.table("notification_history").insert(data).execute()

def delete_old_notifications(days=7):
    """Delete notification_history records older than specified days.
    
    Args:
        days: Number of days to keep (default: 7)
    """
    client = get_supabase()
    if not client:
        return
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        client.table("notification_history") \
            .delete() \
            .lt("sent_at", cutoff.isoformat()) \
            .execute()
    except Exception as e:
        # Log error but don't fail the operation
        import logging
        logging.getLogger(__name__).warning(f"Failed to delete old notifications: {e}")

def record_last_check_time():
    """Record the current time as the last check time.
    
    Updates the single row in system_status table or creates it if it doesn't exist.
    """
    client = get_supabase()
    if not client:
        return
    from datetime import datetime, timezone
    current_time = datetime.now(timezone.utc).isoformat()
    try:
        # Try to update existing row
        response = client.table("system_status") \
            .update({"last_check_at": current_time}) \
            .eq("id", 1) \
            .execute()
        # If no rows were updated, insert new row
        if not response.data:
            client.table("system_status").insert({
                "id": 1,
                "last_check_at": current_time
            }).execute()
    except Exception as e:
        # Table might not exist yet, log warning
        import logging
        logging.getLogger(__name__).warning(f"Failed to record last check time: {e}")

def get_last_check_time():
    """Get the last check time from the database.
    
    Returns:
        datetime object or None if not found/error
    """
    client = get_supabase()
    if not client:
        return None
    try:
        response = client.table("system_status") \
            .select("last_check_at") \
            .eq("id", 1) \
            .execute()
        if response.data:
            from datetime import datetime
            # Parse ISO format string to datetime
            return datetime.fromisoformat(response.data[0]["last_check_at"].replace("Z", "+00:00"))
    except Exception as e:
        # Table might not exist or other error
        import logging
        logging.getLogger(__name__).warning(f"Failed to get last check time: {e}")
    return None
def delete_history_by_setting(setting_id):
    """Delete all notification history for a specific setting ID."""
    client = get_supabase()
    if not client:
        return False
    try:
        client.table("notification_history") \
            .delete() \
            .eq("setting_id", setting_id) \
            .execute()
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to delete history for setting {setting_id}: {e}")
        return False

#XB|
def delete_all_history():
    """Delete all notification history records from the database."""
    client = get_supabase()
    if not client:
        return False
    try:
        # Supabase delete without filters will delete all rows if the table policy allows it
        client.table("notification_history") \
            .delete() \
            .neq("id", -1) \
            .execute()
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to delete all notification history: {e}")
        return False
#XB|
