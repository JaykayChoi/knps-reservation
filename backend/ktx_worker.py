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


class ConsecutiveFailureGuard:
    """Disable monitors after repeated provider query failures in this process."""

    def __init__(self, monitors, threshold=3):
        self.monitors = monitors
        self.threshold = threshold
        self.failures = {}

    def apply(self, summary):
        for monitor_id in summary.query_succeeded:
            self.failures.pop(monitor_id, None)
        for monitor_id in summary.query_failed:
            count = min(self.failures.get(monitor_id, 0) + 1, self.threshold)
            self.failures[monitor_id] = count
            logger.warning('KTX monitor %s query failure %s/%s',
                           monitor_id, count, self.threshold)
            if count < self.threshold:
                continue
            try:
                self.monitors.update(monitor_id, {'is_active': False})
            except Exception:
                logger.exception('Could not deactivate KTX monitor %s', monitor_id)
                continue
            self.failures.pop(monitor_id, None)
            logger.error('KTX monitor %s deactivated after %s consecutive failures',
                         monitor_id, self.threshold)


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
    failure_guard = ConsecutiveFailureGuard(monitors)

    def check():
        summary = checks.run(categories={'ktx'})
        failure_guard.apply(summary)
        return summary

    run_scheduler(check)


if __name__ == '__main__':
    main()
