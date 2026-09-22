import logging

import requests

from domain.models import DeliveryResult

logger = logging.getLogger(__name__)


class TelegramSender:
    def __init__(self, session=None, timeout=10):
        self.session = session or requests.Session()
        self.timeout = timeout

    def send(self, batch):
        if not batch.bot_token or not batch.chat_id:
            return DeliveryResult(False, 'Telegram credentials are missing')
        if not batch.items or not batch.text:
            return DeliveryResult(False, 'Notification batch is empty')
        try:
            response = self.session.post(
                f'https://api.telegram.org/bot{batch.bot_token}/sendMessage',
                json={
                    'chat_id': batch.chat_id,
                    'text': batch.text,
                    'disable_web_page_preview': True,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or payload.get('ok') is not True:
                raise ValueError('Telegram rejected the message')
            return DeliveryResult(True)
        except Exception as exc:
            logger.error('Telegram delivery failed for monitor %s (%s)',
                         batch.monitor_id, type(exc).__name__)
            return DeliveryResult(False, 'Telegram delivery failed')
