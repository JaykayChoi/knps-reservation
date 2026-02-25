import pytest
import os
import configparser
from flask import json
import sys

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import db
import notifier
from app import app as flask_app

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client

@pytest.fixture
def telegram_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    if not os.path.exists('config.ini'):
        return {
            'token': os.environ.get('TELEGRAM_BOT_TOKEN', 'dummy'),
            'chat_id': os.environ.get('TELEGRAM_CHAT_ID', 'dummy')
        }
    return {
        'token': config.get('telegram', 'bot_token'),
        'chat_id': config.get('telegram', 'chat_id')
    }

def test_update_settings_success(client):
    test_data = {
        "weeks_ahead": 4,
        "start_date": "2026-03-01",
        "end_date": "2026-03-31",
        "cooldown_days": 1,
        "telegram_bot_token": "test_token",
        "telegram_chat_id": "test_chat_id",
        "include_waiting": True,
        "selected_days": ["Fri", "Sat"],
        "selected_types": ["카라반"],
        "selected_parks": ["덕유산"]
    }
    response = client.post('/api/settings', data=json.dumps(test_data), content_type='application/json')
    assert response.status_code == 200
    assert response.get_json() == {"success": True}

def test_telegram_test_notification(telegram_config):
    if telegram_config['token'] == 'dummy':
        pytest.skip("Telegram token not configured")
        
    dummy_res = [{
        'date': '20260301',
        'park_name': '테스트공원',
        'campsite_name': '테스트야영장',
        'facility_type': '테스트시설',
        'available_count': 1,
        'waiting_count': 0
    }]
    success = notifier.send_telegram_notification(
        telegram_config['token'],
        telegram_config['chat_id'],
        dummy_res,
        is_test=True
    )
    assert success is True
