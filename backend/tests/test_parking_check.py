import os
import sys
from unittest.mock import patch

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import PARKING_HISTORY_DATE, run_parking_check


def _setting(**overrides):
    base = {
        "id": 1,
        "name": "Monitor",
        "selected_parkinglots": ["109902"],
        "telegram_bot_token": "token",
        "telegram_chat_id": "chat",
        "cooldown_days": 3,
    }
    base.update(overrides)
    return base


def _pass(seq=109902, name="투루파킹 KT&G타워 주차장", available=True):
    return {
        "lot_seq": seq,
        "lot_name": name,
        "ticket_name": "월정기권",
        "coupon_seq": 22453,
        "price": 242000,
        "is_available": available,
        "url": f"https://app.modu.kr/map?type=P&id={seq}#sheet=2",
    }


@patch('app.modu_scraper.fetch_monthly_passes')
def test_no_watchers_skips_fetch(mock_fetch):
    summary = run_parking_check([_setting(selected_parkinglots=[]), {"id": 2}])

    mock_fetch.assert_not_called()
    assert summary == {"lots_checked": 0, "available": 0, "notified": 0}


@patch('app.db.record_notification')
@patch('app.db.check_cooldown', return_value=False)
@patch('app.notifier.send_parking_notification', return_value=True)
@patch('app.modu_scraper.fetch_monthly_passes')
def test_available_pass_triggers_notification(mock_fetch, mock_send, mock_cooldown, mock_record):
    mock_fetch.return_value = [_pass()]

    summary = run_parking_check([_setting()], is_test=True)

    assert summary == {"lots_checked": 1, "available": 1, "notified": 1}
    mock_send.assert_called_once()
    args, kwargs = mock_send.call_args
    assert args[0] == "token" and args[1] == "chat"
    assert args[2][0]["lot_seq"] == 109902
    assert kwargs["is_test"] is True
    mock_record.assert_called_once_with(
        1, PARKING_HISTORY_DATE, "투루파킹 KT&G타워 주차장", "월정기권", False
    )


@patch('app.notifier.send_parking_notification')
@patch('app.modu_scraper.fetch_monthly_passes')
def test_sold_out_pass_does_not_notify(mock_fetch, mock_send):
    mock_fetch.return_value = [_pass(available=False)]

    summary = run_parking_check([_setting()])

    assert summary == {"lots_checked": 1, "available": 0, "notified": 0}
    mock_send.assert_not_called()


@patch('app.db.record_notification')
@patch('app.db.check_cooldown', return_value=True)
@patch('app.notifier.send_parking_notification')
@patch('app.modu_scraper.fetch_monthly_passes')
def test_cooldown_suppresses_notification(mock_fetch, mock_send, mock_cooldown, mock_record):
    mock_fetch.return_value = [_pass()]

    summary = run_parking_check([_setting()])

    assert summary["available"] == 1
    assert summary["notified"] == 0
    mock_send.assert_not_called()
    mock_record.assert_not_called()
    mock_cooldown.assert_called_once_with(
        1, PARKING_HISTORY_DATE, "투루파킹 KT&G타워 주차장", "월정기권", False, 3
    )


@patch('app.db.check_cooldown', return_value=False)
@patch('app.notifier.send_parking_notification', return_value=True)
@patch('app.modu_scraper.fetch_monthly_passes')
def test_only_selected_lots_are_notified(mock_fetch, mock_send, mock_cooldown):
    mock_fetch.return_value = [_pass(), _pass(seq=106112, name="카카오 T 대치사거리 주차장")]

    with patch('app.db.record_notification'):
        summary = run_parking_check([_setting(selected_parkinglots=["106112"])])

    assert summary["available"] == 2
    assert summary["notified"] == 1
    sent = mock_send.call_args[0][2]
    assert [p["lot_seq"] for p in sent] == [106112]


@patch('app.db.check_cooldown', return_value=False)
@patch('app.notifier.send_parking_notification', return_value=True)
@patch('app.modu_scraper.fetch_monthly_passes')
def test_lots_are_fetched_once_across_settings(mock_fetch, mock_send, mock_cooldown):
    mock_fetch.return_value = [_pass()]
    settings = [_setting(id=1), _setting(id=2, selected_parkinglots=["109902", "106112"])]

    with patch('app.db.record_notification'):
        run_parking_check(settings)

    mock_fetch.assert_called_once_with(["106112", "109902"])


@patch('app.db.record_notification')
@patch('app.db.check_cooldown', return_value=False)
@patch('app.notifier.send_parking_notification')
@patch('app.modu_scraper.fetch_monthly_passes')
def test_missing_telegram_credentials_skipped(mock_fetch, mock_send, mock_cooldown, mock_record):
    mock_fetch.return_value = [_pass()]

    summary = run_parking_check([_setting(telegram_chat_id="")])

    assert summary["notified"] == 0
    mock_send.assert_not_called()
    mock_record.assert_not_called()


@patch('app.db.check_cooldown', return_value=False)
@patch('app.notifier.send_parking_notification', return_value=False)
@patch('app.db.record_notification')
@patch('app.modu_scraper.fetch_monthly_passes')
def test_failed_send_is_not_recorded(mock_fetch, mock_record, mock_send, mock_cooldown):
    mock_fetch.return_value = [_pass()]

    summary = run_parking_check([_setting()])

    assert summary["notified"] == 0
    mock_record.assert_not_called()


@patch('app.modu_scraper.fetch_monthly_passes', side_effect=Exception("network down"))
def test_scraper_failure_is_isolated(mock_fetch):
    """주차장 조회 실패가 국립공원 확인 로직을 중단시키면 안 된다."""
    summary = run_parking_check([_setting()])

    assert summary == {"lots_checked": 0, "available": 0, "notified": 0}
