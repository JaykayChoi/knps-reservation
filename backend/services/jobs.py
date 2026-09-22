from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Lock


class CheckRunner:
    def __init__(self, run_check, executor=None):
        self.run_check = run_check
        self.executor = executor
        self._future = None
        self._lock = Lock()

    def submit(self, *, is_test=False):
        with self._lock:
            if self._future is not None and not self._future.done():
                return 'running'
            if self.executor is None:
                self.executor = ThreadPoolExecutor(max_workers=1,
                                                   thread_name_prefix='monitor-check')
            self._future = self.executor.submit(self.run_check, is_test=is_test)
            return 'queued'

    def shutdown(self, wait=True):
        if self.executor is not None:
            self.executor.shutdown(wait=wait)


class MaintenanceService:
    def __init__(self, history, clock, retention_days=31):
        self.history = history
        self.clock = clock
        self.retention_days = max(31, retention_days)

    def run(self):
        now = self.clock()
        reset = self.history.reset_for_kst_day()
        self.history.delete_older_than(now - timedelta(days=self.retention_days))
        return reset
