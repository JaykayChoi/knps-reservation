"""Run active KTX monitors from this machine without an HTTP server."""

import logging
import random
import time

from config import load_environment
from domain.clock import Clock
from notifications.telegram import TelegramSender
from providers import ktx
from providers.registry import KtxProvider
from repositories.client import create_supabase_client
from repositories.history import HistoryRepository
from repositories.monitors import MonitorRepository
from services.checks import CheckService
from services.notifications import NotificationService


logger = logging.getLogger(__name__)


def run_scheduler(check, *, wait=time.sleep, random_delay=random.randint,
                  should_stop=lambda: False):
    while not should_stop():
        try:
            summary = check()
            logger.info('KTX check complete: %s', summary.as_dict())
        except Exception:
            logger.exception('KTX check failed')
        delay = random_delay(120, 300)
        logger.info('Next KTX check in %s seconds', delay)
        wait(delay)


def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    load_environment()
    client = create_supabase_client()
    monitors = MonitorRepository(client)
    history = HistoryRepository(client)
    clock = Clock()
    notifications = NotificationService(monitors, history, TelegramSender(), clock.now)
    checks = CheckService(monitors, {'ktx': KtxProvider(ktx.fetch_availability)},
                          notifications, clock.now)
    run_scheduler(lambda: checks.run(categories={'ktx'}))


if __name__ == '__main__':
    main()
