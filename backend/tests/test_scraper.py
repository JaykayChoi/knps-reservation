import pytest
import datetime
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scraper import get_target_dates, fetch_reservations
from unittest.mock import patch, MagicMock

def test_get_target_dates_weekday_mode(mocker):
    """Test weekday mode date calculation."""
    # Mock today as a Monday (2026-02-23 is Monday)
    import scraper
    mock_datetime = mocker.patch('scraper.datetime')
    mock_datetime.date.today.return_value = datetime.date(2026, 2, 23)
    mock_datetime.timedelta = datetime.timedelta
    # 1 week ahead, only Fridays (4)
    weeks = 1
    selected_days = [4]
    specific_dates = []
    
    dates = scraper.get_target_dates(weeks, selected_days, specific_dates, date_mode="weekday")
    # In the week of Feb 23, Friday is Feb 27
    assert "20260227" in dates
    assert len(dates) == 1
def test_get_target_dates_absolute_mode():
    """Test absolute mode date calculation."""
    weeks = 0
    selected_days = []
    specific_dates = ["2026-05-05", "20260506"]
    dates = get_target_dates(weeks, selected_days, specific_dates, date_mode="absolute")
    assert "20260505" in dates
    assert "20260506" in dates
    assert len(dates) == 2
def test_get_target_dates_absolute_mode_invalid_dates():
    """Test absolute mode with invalid date formats."""
    weeks = 0
    selected_days = []
    specific_dates = ["2026-05-05", "invalid", "2026.05.07", "20260508"]
    dates = get_target_dates(weeks, selected_days, specific_dates, date_mode="absolute")
    # Should only include valid dates
    assert "20260505" in dates
    assert "20260507" in dates  # 2026.05.07 should be cleaned
    assert "20260508" in dates
    assert len(dates) == 3
    assert "invalid" not in dates
def test_get_target_dates_weekday_mode_no_days():
    """Test weekday mode with no selected days."""
    weeks = 2
    selected_days = []
    specific_dates = []
    
    dates = get_target_dates(weeks, selected_days, specific_dates, date_mode="weekday")
    
    # Should return empty set
    assert len(dates) == 0

def test_get_target_dates_absolute_mode_no_dates():
    """Test absolute mode with no specific dates."""
    weeks = 0
    selected_days = []
    specific_dates = []
    
    dates = get_target_dates(weeks, selected_days, specific_dates, date_mode="absolute")
    
    # Should return empty set
    assert len(dates) == 0

def test_get_target_dates_default_mode(mocker):
    """Test default mode (weekday) when date_mode not specified."""
    import scraper
    mock_datetime = mocker.patch('scraper.datetime')
    mock_datetime.date.today.return_value = datetime.date(2026, 2, 23)
    mock_datetime.timedelta = datetime.timedelta
    weeks = 1
    selected_days = [4]
    specific_dates = []
    
    dates = scraper.get_target_dates(weeks, selected_days, specific_dates)
    
    # Should use weekday mode by default
    assert "20260227" in dates
    assert len(dates) == 1

def _mock_session_with_json(json_payload):
    session = MagicMock()
    response = MagicMock()
    response.json.return_value = json_payload
    response.raise_for_status.return_value = None
    session.post.return_value = response
    return session


@patch('scraper._build_session')
def test_fetch_reservations_success(mock_build_session):
    mock_build_session.return_value = _mock_session_with_json({
        "list": [
            {"officeNm": "덕유산", "deptNm": "덕유산야영장", "prdCtgNm": "카라반", "cntN": 5},
            {"officeNm": "치악산", "deptNm": "치악산야영장", "prdCtgNm": "자동차야영장", "cntN": 0},
        ]
    })

    results = fetch_reservations(["20260301"], ["카라반"], ["덕유산"])

    assert len(results) == 1
    assert results[0]["park_name"] == "덕유산"
    assert results[0]["available_count"] == 5
    assert results[0]["waiting_count"] == 0


@patch('scraper._build_session')
def test_fetch_reservations_waiting_list(mock_build_session):
    mock_build_session.return_value = _mock_session_with_json({
        "list": [
            {"officeNm": "가야산", "deptNm": "백운동", "prdCtgNm": "자동차야영장", "cntN": 0, "cntW": 2}
        ]
    })

    results = fetch_reservations(["20260301"], ["자동차야영장"], ["가야산"])

    assert len(results) == 1
    assert results[0]["available_count"] == 0
    assert results[0]["waiting_count"] == 2


@patch('scraper._build_session')
def test_fetch_reservations_returns_empty_when_login_fails(mock_build_session):
    mock_build_session.return_value = None
    results = fetch_reservations(["20260301"], [], [])
    assert results == []


@patch('scraper._build_session')
def test_fetch_reservations_handles_null_list(mock_build_session):
    mock_build_session.return_value = _mock_session_with_json({"list": None})
    results = fetch_reservations(["20260301"], [], [])
    assert results == []

