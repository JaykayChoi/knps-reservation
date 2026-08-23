import pytest
import os
import configparser
from flask import json
import sys
from unittest.mock import patch

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

@patch('app.db.update_settings')
def test_update_settings_success(mock_update, client):
    """POST /api/settings 라우트 계약만 검증한다.

    db.update_settings 를 반드시 목킹할 것: 이 엔드포인트는 setting_id 가 없으면
    '첫 번째 활성 설정'을 덮어쓰므로, 목킹하지 않으면 .env 가 가리키는 실제
    Supabase 의 사용자 설정이 테스트 데이터로 파괴된다.
    """
    test_data = {
        "weeks_ahead": 4,
        "start_date": "2026-03-01",
        "end_date": "2026-03-31",
        "cooldown_days": 0,
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
    mock_update.assert_called_once_with(test_data)

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
