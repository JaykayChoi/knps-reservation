from copy import deepcopy
from datetime import datetime, timezone

from domain.models import Availability, DeliveryResult, HistoryKey, QueryResult
from services.checks import CheckService
from services.notifications import NotificationService

NOW = datetime(2026, 9, 22, 3, 0, tzinfo=timezone.utc)


def monitor(**overrides):
    value = {
        'id': 1, 'name': 'Train', 'category': 'ktx', 'is_active': True,
        'options': {'departure': '서울', 'arrival': '부산', 'date': '2099-10-01',
                    'start_time': '08:00', 'end_time': '18:00',
                    'seat_classes': ['general']},
        'cooldown_days': 3, 'quiet_hours_enabled': False,
        'quiet_hours_start': '23:00', 'quiet_hours_end': '07:00',
        'telegram_bot_token': 'token', 'telegram_chat_id': 'chat',
    }
    value.update(overrides)
    return value


def availability(index=1):
    return Availability('ktx', HistoryKey('20991001', '서울→부산', f'{index}:general'), {
        'date': '20991001', 'departure': '서울', 'arrival': '부산',
        'train_no': str(index), 'departure_time': '090000',
        'arrival_time': '120000', 'seat_class': 'general',
    })


class MonitorRepo:
    def __init__(self, rows):
        self.rows = {row['id']: deepcopy(row) for row in rows}

    def list(self, active_only=False):
        rows = list(self.rows.values())
        return [deepcopy(row) for row in rows if not active_only or row['is_active']]

    def get(self, monitor_id):
        row = self.rows.get(monitor_id)
        return deepcopy(row) if row else None


class HistoryRepo:
    def __init__(self, cooldown=None, fail_record=False):
        self.cooldown = set(cooldown or [])
        self.recorded = []
        self.fail_record = fail_record

    def is_on_cooldown(self, monitor_id, key, cooldown_days, now):
        return key in self.cooldown

    def record_batch(self, monitor_id, keys, sent_at):
        if self.fail_record:
            raise RuntimeError('db unavailable')
        self.recorded.append((monitor_id, tuple(keys)))


class Sender:
    def __init__(self, results=None, before_send=None):
        self.results = list(results or [True])
        self.before_send = before_send
        self.batches = []

    def send(self, batch):
        if self.before_send:
            self.before_send(len(self.batches))
        self.batches.append(batch)
        delivered = self.results.pop(0) if self.results else True
        return DeliveryResult(delivered, None if delivered else 'failed')


def test_notification_filters_cooldown_and_records_only_successful_batch():
    current = monitor()
    history = HistoryRepo(cooldown={availability(2).history})
    sender = Sender()
    service = NotificationService(MonitorRepo([current]), history, sender, lambda: NOW)

    outcome = service.notify(current, (availability(1), availability(2)))

    assert outcome.notified == 1
    assert outcome.messages == 1
    assert len(sender.batches[0].items) == 1
    assert history.recorded == [(1, (availability(1).history,))]


def test_zero_cooldown_and_test_delivery_do_not_touch_history():
    for current, is_test in [(monitor(cooldown_days=0), False), (monitor(), True)]:
        history = HistoryRepo()
        outcome = NotificationService(MonitorRepo([current]), history, Sender(), lambda: NOW).notify(
            current, (availability(),), is_test=is_test)
        assert outcome.notified == 1
        assert history.recorded == []


def test_failed_batch_is_not_recorded_and_history_failure_is_reported():
    current = monitor()
    failed_history = HistoryRepo(fail_record=True)
    failed_delivery = NotificationService(
        MonitorRepo([current]), HistoryRepo(), Sender([False]), lambda: NOW,
    ).notify(current, (availability(),))
    history_failure = NotificationService(
        MonitorRepo([current]), failed_history, Sender(), lambda: NOW,
    ).notify(current, (availability(),))

    assert failed_delivery.notified == 0 and failed_delivery.errors
    assert history_failure.notified == 1 and history_failure.errors


def test_latest_monitor_change_or_quiet_time_discards_stale_batches():
    current = monitor()
    repo = MonitorRepo([current])
    repo.rows[1]['is_active'] = False
    sender = Sender()
    outcome = NotificationService(repo, HistoryRepo(), sender, lambda: NOW).notify(
        current, tuple(availability(i) for i in range(21)))
    assert outcome.notified == 0

    quiet = monitor(quiet_hours_enabled=True, quiet_hours_start='11:00', quiet_hours_end='13:00')
    quiet_outcome = NotificationService(
        MonitorRepo([quiet]), HistoryRepo(), Sender(), lambda: NOW,
    ).notify(quiet, (availability(),))
    assert quiet_outcome.skipped_quiet


class Provider:
    def __init__(self, result=None, error=None):
        self.result = result or QueryResult((availability(),))
        self.error = error
        self.calls = []

    def fetch(self, options):
        self.calls.append(deepcopy(options))
        if self.error:
            raise self.error
        return self.result


class Notifications:
    def __init__(self):
        self.calls = []

    def notify(self, current, items, is_test=False):
        self.calls.append((current['id'], tuple(items), is_test))
        from services.notifications import NotificationOutcome
        return NotificationOutcome(notified=len(items), messages=1 if items else 0)


def test_check_service_caches_identical_queries_and_isolates_errors():
    first = monitor(id=1)
    second = monitor(id=2)
    broken = monitor(id=3, category='broken', options={})
    provider = Provider()
    notifications = Notifications()
    service = CheckService(MonitorRepo([first, second, broken]),
                           {'ktx': provider, 'broken': Provider(error=RuntimeError('secret'))},
                           notifications, lambda: NOW)

    summary = service.run()

    assert len(provider.calls) == 1
    assert [call[0] for call in notifications.calls] == [1, 2]
    assert summary.checked == 3 and summary.available == 2 and summary.notified == 2
    assert len(summary.errors) == 1 and 'secret' not in summary.errors[0]


def test_check_service_caches_identical_query_failures_for_one_run():
    first = monitor(id=1)
    second = monitor(id=2)
    provider = Provider(error=RuntimeError('blocked'))

    summary = CheckService(MonitorRepo([first, second]), {'ktx': provider},
                           Notifications(), lambda: NOW).run(categories={'ktx'})

    assert len(provider.calls) == 1
    assert summary.query_failed == {1, 2}


def test_check_service_skips_quiet_monitor_before_provider_call():
    quiet = monitor(quiet_hours_enabled=True, quiet_hours_start='11:00', quiet_hours_end='13:00')
    provider = Provider()
    summary = CheckService(MonitorRepo([quiet]), {'ktx': provider}, Notifications(), lambda: NOW).run()
    assert provider.calls == []
    assert summary.skipped_quiet == 1


def test_check_service_only_checks_selected_active_category():
    active_ktx = monitor(id=1)
    inactive_ktx = monitor(id=2, is_active=False)
    active_knps = monitor(id=3, category='knps', options={})
    provider = Provider()
    notifications = Notifications()
    summary = CheckService(
        MonitorRepo([active_ktx, inactive_ktx, active_knps]),
        {'ktx': provider, 'knps': Provider()}, notifications, lambda: NOW,
    ).run(categories={'ktx'})

    assert summary.checked == 1
    assert len(provider.calls) == 1
    assert [call[0] for call in notifications.calls] == [1]


def test_ktx_category_filter_does_not_query_during_quiet_hours():
    quiet = monitor(quiet_hours_enabled=True, quiet_hours_start='11:00',
                    quiet_hours_end='13:00')
    provider = Provider()
    summary = CheckService(MonitorRepo([quiet]), {'ktx': provider},
                           Notifications(), lambda: NOW).run(categories={'ktx'})

    assert summary.checked == 1
    assert summary.skipped_quiet == 1
    assert provider.calls == []


def test_check_summary_tracks_query_success_failure_and_not_quiet_skips():
    success = monitor(id=1)
    failure = monitor(id=2, options={**monitor()['options'], 'date': '2099-10-02'})
    quiet = monitor(id=3, options={**monitor()['options'], 'date': '2099-10-03'},
                    quiet_hours_enabled=True, quiet_hours_start='11:00',
                    quiet_hours_end='13:00')
    successful_provider = Provider()

    class SelectiveProvider:
        def fetch(self, options):
            if options['date'] == '2099-10-02':
                raise RuntimeError('blocked')
            return successful_provider.fetch(options)

    summary = CheckService(
        MonitorRepo([success, failure, quiet]), {'ktx': SelectiveProvider()},
        Notifications(), lambda: NOW,
    ).run(categories={'ktx'})

    assert summary.query_succeeded == {1}
    assert summary.query_failed == {2}
