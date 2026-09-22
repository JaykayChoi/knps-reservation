from services.checks import CheckSummary
from ktx_worker import ConsecutiveFailureGuard, run_scheduler


def test_scheduler_checks_immediately_then_draws_a_new_delay_each_time():
    events = []
    delays = iter((120, 300))
    checks = 0

    def check():
        nonlocal checks
        checks += 1
        events.append('check')

    def wait(seconds):
        events.append(('wait', seconds))

    run_scheduler(check, wait=wait,
                  random_delay=lambda start, end: next(delays),
                  should_stop=lambda: checks == 2)

    assert events == ['check', ('wait', 120), 'check', ('wait', 300)]


def test_scheduler_waits_after_a_failed_check():
    events = []

    def check():
        events.append('check')
        raise RuntimeError('provider unavailable')

    def wait(seconds):
        events.append(('wait', seconds))

    run_scheduler(check, wait=wait,
                  random_delay=lambda start, end: 180,
                  should_stop=lambda: len(events) == 2)

    assert events == ['check', ('wait', 180)]


class MonitorRepo:
    def __init__(self):
        self.updates = []

    def update(self, monitor_id, values):
        self.updates.append((monitor_id, values))


def summary(*, succeeded=(), failed=()):
    return CheckSummary(query_succeeded=set(succeeded), query_failed=set(failed))


def test_failure_guard_disables_after_three_consecutive_query_failures():
    monitors = MonitorRepo()
    guard = ConsecutiveFailureGuard(monitors, threshold=3)

    guard.apply(summary(failed=[7]))
    guard.apply(summary(failed=[7]))
    assert monitors.updates == []

    guard.apply(summary(failed=[7]))
    assert monitors.updates == [(7, {'is_active': False})]
    assert 7 not in guard.failures


def test_failure_guard_resets_on_success_and_ignores_unreported_monitors():
    monitors = MonitorRepo()
    guard = ConsecutiveFailureGuard(monitors, threshold=3)

    guard.apply(summary(failed=[7]))
    guard.apply(summary())  # quiet hours or not checked
    assert guard.failures[7] == 1
    guard.apply(summary(succeeded=[7]))
    assert 7 not in guard.failures

    guard.apply(summary(failed=[7]))
    guard.apply(summary(failed=[7]))
    assert monitors.updates == []


def test_failure_guard_keeps_threshold_count_when_deactivation_write_fails():
    class FailingRepo(MonitorRepo):
        def update(self, monitor_id, values):
            raise RuntimeError('database unavailable')

    guard = ConsecutiveFailureGuard(FailingRepo(), threshold=3)
    guard.apply(summary(failed=[7]))
    guard.apply(summary(failed=[7]))

    try:
        guard.apply(summary(failed=[7]))
    except RuntimeError:
        pass

    assert guard.failures[7] == 3
