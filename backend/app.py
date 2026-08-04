from flask import Flask, request, jsonify
from flask_cors import CORS
import db
import scraper
import modu_scraper
import notifier
import os
import random
import logging
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

# 주차장 월정기권은 날짜 개념이 없어 이력 키의 target_date 자리에 상수를 쓴다.
PARKING_HISTORY_DATE = "MONTHLY"

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
        logger.info(f"Creating new setting with data: {data}")
        new_setting = db.create_settings(data)
        if not new_setting:
            logger.error("create_settings returned None")
            return jsonify({"error": "Failed to create setting"}), 500
        logger.info(f"Setting created successfully: id={new_setting.get('id')}")
        return jsonify({"success": True, "setting": new_setting})
    except ValueError as e:
        logger.warning(f"ValueError in PUT /api/settings: {e}")
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
@app.route("/api/search", methods=["GET"])
def search_availability():
    try:
        raw_dates = request.args.get("dates", "")
        raw_types = request.args.get("types", "")
        raw_parks = request.args.get("parks", "")
        
        date_input = raw_dates if raw_dates else request.args.get("date")
        if not date_input:
            return jsonify({"error": "Date is required"}), 400
            
        target_dates = [d.strip().replace("-", "") for d in date_input.split(",") if d.strip()]
        facility_types = [t.strip() for t in raw_types.split(",") if t.strip()]
        parks = [p.strip() for p in raw_parks.split(",") if p.strip()]
        
        results = scraper.fetch_reservations(target_dates, facility_types, parks)
        return jsonify(results)
    except Exception as e:
        logger.exception("Error in /api/search")
        return jsonify({"error": str(e)}), 500

@app.route("/api/history", methods=["DELETE"])
def delete_all_history():
    try:
        success = db.delete_all_history()
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Failed to delete all history"}), 500
    except Exception as e:
        logger.exception("Error in DELETE /api/history")
        return jsonify({"error": str(e)}), 500
@app.route("/api/parking-lots", methods=["GET"])
def get_parking_lots():
    """Monitorable 모두의주차장 parking lots (fixed list)."""
    return jsonify(modu_scraper.get_parking_lots())


def run_parking_check(all_settings, is_test=False):
    """Check 모두의주차장 monthly passes for every setting that watches a lot.

    Runs on every /api/check call regardless of the probability gate: monthly
    passes are released whenever someone cancels, not on a fixed schedule.
    """
    summary = {"lots_checked": 0, "available": 0, "notified": 0}
    try:
        watchers = [s for s in all_settings if s.get("selected_parkinglots")]
        if not watchers:
            return summary

        # 여러 설정이 같은 주차장을 봐도 조회는 합집합으로 1번만.
        wanted = sorted({str(seq) for s in watchers for seq in (s.get("selected_parkinglots") or [])})
        passes = modu_scraper.fetch_monthly_passes(wanted)
        summary["lots_checked"] = len(wanted)

        available = [p for p in passes if p["is_available"]]
        summary["available"] = len(available)
        if not available:
            return summary

        for settings in watchers:
            token = settings.get("telegram_bot_token")
            chat_id = settings.get("telegram_chat_id")
            if not token or not chat_id:
                continue

            s_id = settings.get("id")
            selected = {str(seq) for seq in (settings.get("selected_parkinglots") or [])}
            cooldown_days = settings.get("cooldown_days", 3)

            to_notify = []
            for item in available:
                if str(item["lot_seq"]) not in selected:
                    continue
                if db.check_cooldown(
                    s_id, PARKING_HISTORY_DATE, item["lot_name"], item["ticket_name"], False, cooldown_days
                ):
                    continue
                to_notify.append(item)

            if not to_notify:
                continue

            logger.info(f"Sending parking notification for {len(to_notify)} passes to {chat_id}. is_test={is_test}")
            if notifier.send_parking_notification(token, chat_id, to_notify, is_test=is_test):
                summary["notified"] += len(to_notify)
                for item in to_notify:
                    db.record_notification(
                        s_id, PARKING_HISTORY_DATE, item["lot_name"], item["ticket_name"], False
                    )
    except Exception as e:
        # 주차장 확인 실패가 국립공원 확인을 막지 않도록 격리한다.
        logger.exception(f"Parking check failed: {e}")

    return summary


@app.route("/api/check", methods=["GET", "POST"])
def check_reservations():
    is_test = request.args.get("test") == "true"

    # 주차장 월정기권은 스케줄/확률 게이트와 무관하게 매 호출마다 확인한다.
    try:
        active_settings = db.get_settings()
    except Exception:
        logger.exception("Failed to load settings for parking check")
        active_settings = []
    parking_summary = run_parking_check(active_settings, is_test=is_test)
    logger.info(
        f"[PARKING SUMMARY] lots_checked={parking_summary['lots_checked']} "
        f"available={parking_summary['available']} notified={parking_summary['notified']}"
    )

    # Probability gate: outside 0~1 hour (KST), only run with given probability.
    kst_hour = datetime.now(KST).hour
    if kst_hour not in (0, 1):
        try:
            prob = float(os.environ.get("CHECK_PROBABILITY", "0.2"))
        except ValueError:
            prob = 0.2
        roll = random.random()
        if roll >= prob:
            logger.info(
                f"[CHECK SUMMARY] status=skipped reason=probability_gate "
                f"kst_hour={kst_hour} probability={prob} roll={roll:.4f}"
            )
            return jsonify({
                "status": "Skipped by probability gate",
                "kst_hour": kst_hour,
                "probability": prob,
                "parking": parking_summary,
            })

    check_start_ts = datetime.now()
    total_dates_checked = 0
    total_available_found = 0
    total_res_new = 0
    total_wait_new = 0
    telegram_sends_attempted = 0
    telegram_sends_succeeded = 0
    telegram_items_sent = 0
    try:
        # Clean up old notifications (older than 7 days)
        db.delete_old_notifications(7)
        all_settings = db.get_settings()  # Returns all active settings
        if not all_settings:
            logger.info("[CHECK SUMMARY] No active settings found")
            return jsonify({"error": "No active settings found", "parking": parking_summary}), 404

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
                    try:
                        sd = datetime.strptime(start_date, "%Y-%m-%d").date()
                        ed = datetime.strptime(end_date, "%Y-%m-%d").date()
                        if sd <= ed:
                            span = (ed - sd).days + 1
                            if span > 120: span = 120
                            for i in range(span):
                                dates.append((sd + timedelta(days=i)).strftime("%Y%m%d"))
                    except:
                        pass
            elif date_mode == "absolute":
                # For absolute mode, use start_date and end_date as specific dates
                specific_dates = []
                start_date = settings.get("start_date")
                end_date = settings.get("end_date")
                if start_date and end_date:
                    try:
                        sd = datetime.strptime(start_date, "%Y-%m-%d").date()
                        ed = datetime.strptime(end_date, "%Y-%m-%d").date()
                        if sd <= ed:
                            span = (ed - sd).days + 1
                            if span > 120: span = 120
                            for i in range(span):
                                specific_dates.append((sd + timedelta(days=i)).strftime("%Y-%m-%d"))
                    except:
                        pass
                
                dates = scraper.get_target_dates(
                    None, 
                    [], 
                    specific_dates,
                    date_mode="absolute"
                )
            
            dates = sorted(list(set(dates)))
            total_dates_checked += len(dates)
            # 2. Fetch reservations
            available = scraper.fetch_reservations(
                dates,
                settings.get("selected_types", []),
                settings.get("selected_parks", [])
            )
            total_available_found += len(available)
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
                    if is_res_new:
                        total_res_new += 1
                    if is_wait_new:
                        total_wait_new += 1
            if to_notify:
                all_notifications.append({
                    "setting_id": settings.get("id"),
                    "setting_name": settings.get("name", "Unnamed Setting"),
                    "notifications": to_notify
                })
                total_available += len(to_notify)
        # 4. Notify and Record
        if all_notifications:
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
                telegram_sends_attempted += 1
                success = notifier.send_telegram_notification(
                    telegram_config["token"],
                    telegram_config["chat_id"],
                    telegram_config["notifications"],
                    is_test=is_test
                )
                if success:
                    success_count += 1
                    telegram_sends_succeeded += 1
                    telegram_items_sent += len(telegram_config["notifications"])
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
            elapsed = (datetime.now() - check_start_ts).total_seconds()
            if success_count > 0:
                # Record the check time
                db.record_last_check_time()

                logger.info(
                    f"[CHECK SUMMARY] status=notified settings={len(all_settings)} "
                    f"dates_checked={total_dates_checked} available_items={total_available_found} "
                    f"new_to_notify={total_available} (reservation={total_res_new}, waiting={total_wait_new}) "
                    f"telegram_sends={telegram_sends_succeeded}/{telegram_sends_attempted} "
                    f"items_sent={telegram_items_sent} elapsed={elapsed:.2f}s"
                )
                return jsonify({
                    "status": "Notifications sent",
                    "count": total_available,
                    "settings_checked": len(all_settings),
                    "parking": parking_summary,
                })
            else:
                logger.warning(
                    f"[CHECK SUMMARY] status=send_failed settings={len(all_settings)} "
                    f"dates_checked={total_dates_checked} available_items={total_available_found} "
                    f"new_to_notify={total_available} (reservation={total_res_new}, waiting={total_wait_new}) "
                    f"telegram_sends={telegram_sends_succeeded}/{telegram_sends_attempted} "
                    f"items_sent={telegram_items_sent} elapsed={elapsed:.2f}s"
                )
                return jsonify({"status": "Failed to send notifications"}), 500
        # Record the check time
        db.record_last_check_time()

        elapsed = (datetime.now() - check_start_ts).total_seconds()
        logger.info(
            f"[CHECK SUMMARY] status=no_new settings={len(all_settings)} "
            f"dates_checked={total_dates_checked} available_items={total_available_found} "
            f"new_to_notify=0 (reservation=0, waiting=0) "
            f"telegram_sends=0/0 items_sent=0 elapsed={elapsed:.2f}s"
        )
        return jsonify({
            "status": "No new availability found",
            "count": 0,
            "settings_checked": len(all_settings),
            "parking": parking_summary,
        })
    except Exception as e:
        elapsed = (datetime.now() - check_start_ts).total_seconds()
        logger.exception(
            f"[CHECK SUMMARY] status=error dates_checked={total_dates_checked} "
            f"available_items={total_available_found} new_to_notify={total_res_new + total_wait_new} "
            f"(reservation={total_res_new}, waiting={total_wait_new}) "
            f"telegram_sends={telegram_sends_succeeded}/{telegram_sends_attempted} "
            f"items_sent={telegram_items_sent} elapsed={elapsed:.2f}s error={e}"
        )
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)