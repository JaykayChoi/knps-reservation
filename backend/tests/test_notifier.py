import pytest
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from notifier import send_telegram_notification
from unittest.mock import patch, MagicMock

@patch('requests.post')
def test_send_telegram_notification_test_prefix(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    
    token = "test_token"
    chat_id = "test_id"
    reservations = [{
        "date": "20260301",
        "park_name": "덕유산",
        "campsite_name": "덕유산야영장",
        "facility_type": "카라반",
        "available_count": 2,
        "waiting_count": 1
    }]
    
    # Test with is_test=True
    send_telegram_notification(token, chat_id, reservations, is_test=True)
    
    # Verify the message contains [TEST]
    args, kwargs = mock_post.call_args
    message = kwargs['json']['text']
    assert "[TEST]" in message
    assert "덕유산" in message
    assert "2026-03-01" in message
    assert "예약 2" in message
    assert "대기 1" in message

@patch('requests.post')
def test_send_telegram_notification_no_prefix(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    
    token = "test_token"
    chat_id = "test_id"
    reservations = [{"date": "20260301", "park_name": "덕유산", "campsite_name": "X", "facility_type": "Y", "available_count": 1, "waiting_count": 0}]
    
    # Test with is_test=False (default)
    send_telegram_notification(token, chat_id, reservations, is_test=False)
    
    args, kwargs = mock_post.call_args
    message = kwargs['json']['text']
    assert "[TEST]" not in message
    assert "🔔" in message
