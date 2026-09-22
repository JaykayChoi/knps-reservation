import os

import pytest

from domain.models import Availability, DeliveryBatch, HistoryKey
from notifications.telegram import TelegramSender


def test_application_import_and_health_route():
    from app import app
    response = app.test_client().get('/api/health')
    assert response.status_code == 200
    assert response.json == {'status': 'healthy'}


def test_telegram_test_notification():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        pytest.skip('Telegram credentials are not configured')
    item = Availability('knps', HistoryKey('20990101', '테스트공원', '테스트시설'), {})
    batch = DeliveryBatch(0, 'knps', token, chat_id,
                          '[TEST] KNPS monitor integration message', (item,))
    assert TelegramSender().send(batch).delivered
