from concurrent.futures import Future
from datetime import datetime, timezone

from services.jobs import CheckRunner, MaintenanceService


class ImmediateExecutor:
    def __init__(self):
        self.calls = []

    def submit(self, function, *args, **kwargs):
        self.calls.append((function, args, kwargs))
        future = Future()
        try:
            future.set_result(function(*args, **kwargs))
        except Exception as exc:
            future.set_exception(exc)
        return future

    def shutdown(self, wait=True):
        self.shutdown_wait = wait


def test_runner_queues_once_and_reports_running():
    class PendingExecutor:
        def __init__(self):
            self.future = Future()
            self.calls = 0

        def submit(self, *_args, **_kwargs):
            self.calls += 1
            return self.future

        def shutdown(self, wait=True):
            pass

    executor = PendingExecutor()
    runner = CheckRunner(lambda is_test=False: None, executor=executor)
    assert runner.submit() == 'queued'
    assert runner.submit() == 'running'
    assert executor.calls == 1


def test_maintenance_uses_atomic_daily_reset_and_31_day_minimum():
    class History:
        def __init__(self):
            self.cutoff = None
            self.resets = 0

        def reset_for_kst_day(self):
            self.resets += 1

        def delete_older_than(self, cutoff):
            self.cutoff = cutoff

    history = History()
    now = datetime(2026, 9, 22, 0, 0, tzinfo=timezone.utc)
    MaintenanceService(history, lambda: now, retention_days=7).run()
    assert history.resets == 1
    assert (now - history.cutoff).days == 31
