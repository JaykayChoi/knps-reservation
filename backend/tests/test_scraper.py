import pytest
import datetime
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scraper import get_target_dates, fetch_reservations
from unittest.mock import patch, MagicMock

def test_get_target_dates_weekday(mocker):
    # Mock today as a Monday (2026-02-23 is Monday)
    import scraper
    mock_datetime = mocker.patch('scraper.datetime')
    mock_datetime.date.today.return_value = datetime.date(2026, 2, 23)
    mock_datetime.timedelta = datetime.timedelta
    
    # 1 week ahead, only Fridays (4)
    weeks = 1
    selected_days = [4]
    specific_dates = []
    
    dates = scraper.get_target_dates(weeks, selected_days, specific_dates)
    
    # In the week of Feb 23, Friday is Feb 27
    assert "20260227" in dates
    assert len(dates) == 1

def test_get_target_dates_specific():
    weeks = 0
    selected_days = []
    specific_dates = ["2026-05-05", "20260506"]
    
    dates = get_target_dates(weeks, selected_days, specific_dates)
    
    assert "20260505" in dates
    assert "20260506" in dates
    assert len(dates) == 2

@patch('requests.post')
def test_fetch_reservations_success(mock_post):
    # Mock KNPS API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "list": [
            {
                "officeNm": "덕유산",
                "deptNm": "덕유산야영장",
                "prdCtgNm": "카라반",
                "cntN": 5
            },
            {
                "officeNm": "치악산",
                "deptNm": "치악산야영장",
                "prdCtgNm": "자동차야영장",
                "cntN": 0  # No availability
            }
        ]
    }
    mock_post.return_value = mock_response
    
    dates = ["20260301"]
    facility_types = ["카라반"]
    parks = ["덕유산"]
    
    results = fetch_reservations(dates, facility_types, parks)
    
    assert len(results) == 1
    assert results[0]["park_name"] == "덕유산"
    assert results[0]["available_count"] == 5
    assert results[0]["identifier"] == "20260301_덕유산_카라반"
