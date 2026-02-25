from flask import Flask, request, jsonify
from flask_cors import CORS
import db
import scraper
import notifier
import os
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="../frontend", static_url_path="/")

CORS(app)

@app.route("/")
def serve_index():
    return app.send_static_file("index.html")
@app.route("/api/health")
def health_check():
    return jsonify({"status": "healthy"}), 200


@app.route("/api/settings", methods=["GET"])
def get_settings():
    try:
        settings = db.get_settings()
        return jsonify(settings)
    except Exception as e:
        logger.exception("Error in GET /api/settings")
        return jsonify({"error": str(e)}), 500

@app.route("/api/settings", methods=["POST"])
def update_settings():
    try:
        data = request.json
        db.update_settings(data)
        return jsonify({"success": True})
    except Exception as e:
        logger.exception("Error in POST /api/settings")
        return jsonify({"error": str(e)}), 500

@app.route("/api/settings/all", methods=["GET"])
def get_all_settings():
    try:
        settings = db.get_all_settings()
        return jsonify(settings)
    except Exception as e:
        logger.exception("Error in GET /api/settings/all")
        return jsonify({"error": str(e)}), 500

@app.route("/api/settings/<int:setting_id>", methods=["GET"])
def get_setting_by_id(setting_id):
    try:
        setting = db.get_settings(setting_id)
        if not setting:
            return jsonify({"error": "Setting not found"}), 404
        return jsonify(setting)
    except Exception as e:
        logger.exception(f"Error in GET /api/settings/{setting_id}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/settings/<int:setting_id>", methods=["PUT"])
def update_setting_by_id(setting_id):
    try:
        data = request.json
        db.update_settings(data, setting_id)
        return jsonify({"success": True})
    except Exception as e:
        logger.exception(f"Error in PUT /api/settings/{setting_id}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/settings/<int:setting_id>", methods=["DELETE"])
def delete_setting(setting_id):
    try:
        client = db.get_supabase()
        if not client:
            return jsonify({"error": "Database connection failed"}), 500
        
        response = client.table("user_settings").delete().eq("id", setting_id).execute()
        if response.data:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Setting not found"}), 404
    except Exception as e:
        logger.exception(f"Error in DELETE /api/settings/{setting_id}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/settings", methods=["PUT"])
def create_setting():
    try:
        data = request.json
        new_setting = db.create_settings(data)
        if not new_setting:
            return jsonify({"error": "Failed to create setting"}), 500
        return jsonify({"success": True, "setting": new_setting})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Error in PUT /api/settings")
        return jsonify({"error": str(e)}), 500

@app.route("/api/settings/<int:setting_id>/history", methods=["DELETE"])
def delete_setting_history(setting_id):
    try:
        success = db.delete_history_by_setting(setting_id)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Failed to delete history"}), 500
    except Exception as e:
        logger.exception(f"Error in DELETE /api/settings/{setting_id}/history")
        return jsonify({"error": str(e)}), 500
#YZ|@app.route("/api/history", methods=["DELETE"])
#BN|def delete_all_history():
#BJ|    try:
#MY|        success = db.delete_all_history()
#QB|        if success:
#VM|            return jsonify({"success": True})
#ZR|        else:
#BN|            return jsonify({"error": "Failed to delete all history"}), 500
#SB|    except Exception as e:
#ST|        logger.exception("Error in DELETE /api/history")
#YV|        return jsonify({"error": str(e)}), 500
#BK|

@app.route("/api/check", methods=["GET", "POST"])
def check_reservations():
    try:
        # Clean up old notifications (older than 7 days)
        db.delete_old_notifications(7)
        all_settings = db.get_settings()  # Returns all active settings
        if not all_settings:
            return jsonify({"error": "No active settings found"}), 404
        
        all_notifications = []
        total_available = 0
        
        for settings in all_settings:
            # 1. Get target dates based on date_mode
            date_mode = settings.get("date_mode", "weekday")
            
            if date_mode == "weekday":
                day_map = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
                raw_days = settings.get("selected_days", ["Fri", "Sat", "Sun"])
                processed_days = []
                if isinstance(raw_days, list):
                    for d in raw_days:
                        if isinstance(d, int): processed_days.append(d)
                        elif d in day_map: processed_days.append(day_map[d])
                dates = scraper.get_target_dates(
                    settings.get("weeks_ahead", 8), 
                    processed_days or [4, 5, 6], 
                    [],
                    date_mode="weekday"
                )
                
                # Also check specific dates if provided
                start_date = settings.get("start_date")
                end_date = settings.get("end_date")
                if start_date and end_date:
                    import datetime
                    try:
                        sd = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
                        ed = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
                        if sd <= ed:
                            span = (ed - sd).days + 1
                            if span > 120: span = 120
                            for i in range(span):
                                dates.append((sd + datetime.timedelta(days=i)).strftime("%Y%m%d"))
                    except:
                        pass
            elif date_mode == "absolute":
                # For absolute mode, use start_date and end_date as specific dates
                specific_dates = []
                start_date = settings.get("start_date")
                end_date = settings.get("end_date")
                if start_date and end_date:
                    import datetime
                    try:
                        sd = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
                        ed = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
                        if sd <= ed:
                            span = (ed - sd).days + 1
                            if span > 120: span = 120
                            for i in range(span):
                                specific_dates.append((sd + datetime.timedelta(days=i)).strftime("%Y-%m-%d"))
                    except:
                        pass
                
                dates = scraper.get_target_dates(
                    None, 
                    [], 
                    specific_dates,
                    date_mode="absolute"
                )
            
            dates = sorted(list(set(dates)))
            # 2. Fetch reservations
            available = scraper.fetch_reservations(
                dates, 
                settings.get("selected_types", []), 
                settings.get("selected_parks", [])
            )
            # 3. Filter by availability and user preference
            to_notify = []
            cooldown_days = settings.get("cooldown_days", 3)
            include_waiting = settings.get("include_waiting", True)
            s_id = settings.get("id")
            
            for res in available:
                is_res_new = False
                is_wait_new = False
                
                # 1. Check for "Reservation" availability (cntN)
                if res.get("available_count", 0) > 0:
                    if not db.check_cooldown(s_id, res["date"], res["park_name"], res["facility_type"], False, cooldown_days):
                        is_res_new = True
                
                # 2. Check for "Waiting" availability (cntW)
                if include_waiting and res.get("waiting_count", 0) > 0:
                    if not db.check_cooldown(s_id, res["date"], res["park_name"], res["facility_type"], True, cooldown_days):
                        is_wait_new = True
                
                if is_res_new or is_wait_new:
                    # Store which part triggered the notification for recording later
                    res["_is_res_new"] = is_res_new
                    res["_is_wait_new"] = is_wait_new
                    to_notify.append(res)
            if to_notify:
                all_notifications.append({
                    "setting_id": settings.get("id"),
                    "setting_name": settings.get("name", "Unnamed Setting"),
                    "notifications": to_notify
                })
                total_available += len(to_notify)
        # 4. Notify and Record
        if all_notifications:
            # Only prefix [TEST] if explicitly requested via query param
            is_test = request.args.get("test") == "true"
            # Group notifications by Telegram credentials
            notifications_by_telegram = {}
            for notification_group in all_notifications:
                setting = next((s for s in all_settings if s.get("id") == notification_group["setting_id"]), {})
                token = setting.get("telegram_bot_token")
                chat_id = setting.get("telegram_chat_id")
                
                if not token or not chat_id:
                    continue
                    
                key = f"{token}:{chat_id}"
                if key not in notifications_by_telegram:
                    notifications_by_telegram[key] = {
                        "token": token,
                        "chat_id": chat_id,
                        "notifications": []
                    }
                
                notifications_by_telegram[key]["notifications"].extend(notification_group["notifications"])
            
            # Send notifications for each Telegram configuration
            success_count = 0
            for key, telegram_config in notifications_by_telegram.items():
                logger.info(f"Sending notification for {len(telegram_config['notifications'])} items to {telegram_config['chat_id']}. is_test={is_test}")
                success = notifier.send_telegram_notification(
                    telegram_config["token"],
                    telegram_config["chat_id"],
                    telegram_config["notifications"],
                    is_test=is_test
                )
                if success:
                    success_count += 1
                    for res in telegram_config["notifications"]:
                        # Find the setting_id for this notification group
                        # Notifications are already grouped by telegram config, but they might come from multiple settings
                        # We need to find the specific setting_id for this reservation item.
                        item_s_id = None
                        for group in all_notifications:
                            if any(n["date"] == res["date"] and n["park_name"] == res["park_name"] and n["facility_type"] == res["facility_type"] for n in group["notifications"]):
                                item_s_id = group["setting_id"]
                                break
                        
                        if item_s_id:
                            if res.get("_is_res_new"):
                                db.record_notification(item_s_id, res["date"], res["park_name"], res["facility_type"], False)
                            if res.get("_is_wait_new"):
                                db.record_notification(item_s_id, res["date"], res["park_name"], res["facility_type"], True)
            if success_count > 0:
                # Record the check time
                db.record_last_check_time()
                
                return jsonify({"status": "Notifications sent", "count": total_available, "settings_checked": len(all_settings)})
            else:
                return jsonify({"status": "Failed to send notifications"}), 500
        # Record the check time
        db.record_last_check_time()
        
        return jsonify({"status": "No new availability found", "count": 0, "settings_checked": len(all_settings)})
    except Exception as e:
        logger.exception("Error in /api/check")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)