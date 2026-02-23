from flask import Flask, request, jsonify
from flask_cors import CORS
import db
import scraper
import notifier
import os
from datetime import datetime

app = Flask(__name__, static_folder="../frontend", static_url_path="/")

CORS(app)

@app.route("/")
def serve_index():
    return app.send_static_file("index.html")

@app.route("/api/settings", methods=["GET"])
def get_settings():
    settings = db.get_settings()
    return jsonify(settings)

@app.route("/api/settings", methods=["POST"])
def update_settings():
    data = request.json
    db.update_settings(data)
    return jsonify({"success": True})

@app.route("/api/check", methods=["GET", "POST"])
def check_reservations():
    settings = db.get_settings()
    if not settings:
        return jsonify({"error": "No settings found"}), 404

    # 1. Get target dates
    # Map day strings from frontend to Python weekdays
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
        [] # We'll handle start_date/end_date specifically
    )
    
    # Add start_date/end_date range if exists
    start_date = settings.get("start_date")
    end_date = settings.get("end_date")
    if start_date and end_date:
        import datetime
        try:
            sd = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            ed = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            if sd <= ed:
                span = (ed - sd).days + 1
                if span > 120: span = 120 # Cap at 120 days
                for i in range(span):
                    dates.append((sd + datetime.timedelta(days=i)).strftime("%Y%m%d"))
        except:
            pass
    
    # Unique and sorted
    dates = sorted(list(set(dates)))
    
    # 2. Fetch reservations
    available = scraper.fetch_reservations(
        dates, 
        settings.get("selected_types", []), 
        settings.get("selected_parks", [])
    )
    
    # 3. Filter by cooldown
    to_notify = []
    cooldown_days = settings.get("cooldown_days", 3)
    
    for res in available:
        if not db.check_cooldown(res["identifier"], cooldown_days):
            to_notify.append(res)
    
    # 4. Notify and Record
    if to_notify:
        success = notifier.send_telegram_notification(
            settings.get("telegram_bot_token"),
            settings.get("telegram_chat_id"),
            to_notify
        )
        if success:
            for res in to_notify:
                db.record_notification(res["identifier"])
            return jsonify({"status": "Notifications sent", "count": len(to_notify)})
        else:
            return jsonify({"status": "Failed to send notifications"}), 500
    
    return jsonify({"status": "No new availability found", "count": 0})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
