from datetime import datetime
from unittest.mock import patch
from unittest.mock import Mock

import pytest

from app import app
import db


@pytest.mark.parametrize("minute, should_truncate", [(0, True), (1, False)])
def test_midnight_check_truncates_history(minute, should_truncate):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 21, 0, minute, 30, tzinfo=tz)

    with patch("app.datetime", FixedDatetime), \
         patch("app.db.truncate_notification_history") as truncate, \
         patch("app.db.get_settings", return_value=[]), \
         patch("app.run_parking_check", return_value={"lots_checked": 0, "available": 0, "notified": 0}), \
         patch("app.db.delete_old_notifications"):
        app.test_client().get("/api/check")

    assert truncate.called is should_truncate


def test_midnight_truncate_failure_is_reported():
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 21, 0, 0, 30, tzinfo=tz)

    with patch("app.datetime", FixedDatetime), \
         patch("app.db.truncate_notification_history", side_effect=RuntimeError("database unavailable")), \
         patch("app.run_parking_check") as parking:
        response = app.test_client().get("/api/check")

    assert response.status_code == 500
    parking.assert_not_called()


@patch("app.db.record_notification")
@patch("app.db.check_cooldown", return_value=False)
@patch("app.notifier.send_parking_notification", return_value=True)
@patch("app.modu_scraper.fetch_monthly_passes")
def test_zero_cooldown_does_not_record_parking_notification(fetch, send, cooldown, record):
    from test_parking_check import _pass, _setting, run_parking_check

    fetch.return_value = [_pass()]
    summary = run_parking_check([_setting(cooldown_days=0)])

    assert summary["notified"] == 1
    record.assert_not_called()


def test_zero_cooldown_does_not_record_campsite_notification():
    setting = {
        "id": 7, "date_mode": "absolute", "start_date": "2026-09-22",
        "end_date": "2026-09-22", "selected_types": [], "selected_parks": [],
        "telegram_bot_token": "test-token", "telegram_chat_id": "test-chat",
        "cooldown_days": 0,
    }
    reservation = {
        "date": "20260922", "park_name": "Park", "facility_type": "Camp",
        "available_count": 1, "waiting_count": 0,
    }
    with patch("app.db.get_settings", return_value=[setting]), \
         patch("app.db.delete_old_notifications"), \
         patch("app.run_parking_check", return_value={"lots_checked": 0, "available": 0, "notified": 0}), \
         patch("app.db.truncate_notification_history"), \
         patch("app.scraper.get_target_dates", return_value=["20260922"]), \
         patch("app.scraper.fetch_reservations", return_value=[reservation]), \
         patch("app.db.check_cooldown", return_value=False), \
         patch("app.notifier.send_telegram_notification", return_value=True), \
         patch("app.db.record_notification") as record, \
         patch("app.db.record_last_check_time"), \
         patch.dict("app.os.environ", {"CHECK_PROBABILITY": "1"}):
        response = app.test_client().get("/api/check")

    assert response.status_code == 200
    assert response.get_json()["status"] == "Notifications sent"
    record.assert_not_called()


def test_truncate_calls_supabase_rpc():
    client = Mock()
    with patch("db.get_supabase", return_value=client):
        db.truncate_notification_history()

    client.rpc.assert_called_once_with("truncate_notification_history")
    client.rpc.return_value.execute.assert_called_once_with()


def test_same_facility_records_only_setting_with_cooldown():
    base = {
        "date_mode": "absolute", "start_date": "2026-09-22", "end_date": "2026-09-22",
        "selected_types": [], "selected_parks": [],
        "telegram_bot_token": "test-token", "telegram_chat_id": "test-chat",
    }
    settings = [{**base, "id": 1, "cooldown_days": 0},
                {**base, "id": 2, "cooldown_days": 3}]
    reservation = {
        "date": "20260922", "park_name": "Park", "facility_type": "Camp",
        "available_count": 1, "waiting_count": 0,
    }
    with patch("app.db.get_settings", return_value=settings), \
         patch("app.db.delete_old_notifications"), \
         patch("app.run_parking_check", return_value={"lots_checked": 0, "available": 0, "notified": 0}), \
         patch("app.db.truncate_notification_history"), \
         patch("app.scraper.get_target_dates", return_value=["20260922"]), \
         patch("app.scraper.fetch_reservations", return_value=[reservation]), \
         patch("app.db.check_cooldown", return_value=False), \
         patch("app.notifier.send_telegram_notification", return_value=True), \
         patch("app.db.record_notification") as record, \
         patch("app.db.record_last_check_time"), \
         patch.dict("app.os.environ", {"CHECK_PROBABILITY": "1"}):
        response = app.test_client().get("/api/check")

    assert response.status_code == 200
    record.assert_called_once_with(2, "20260922", "Park", "Camp", False)
