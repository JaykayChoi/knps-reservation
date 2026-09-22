from copy import deepcopy
from dataclasses import dataclass, field

from domain.clock import KST
from domain.notification_policy import is_quiet_time
from domain.schedules import knps_target_dates
from providers.registry import query_cache_key


@dataclass
class CheckSummary:
    checked: int = 0
    available: int = 0
    notified: int = 0
    messages: int = 0
    skipped_quiet: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self):
        return {
            'checked': self.checked,
            'available': self.available,
            'notified': self.notified,
            'messages': self.messages,
            'skipped_quiet': self.skipped_quiet,
            'errors': list(self.errors),
        }


class CheckService:
    def __init__(self, monitors, providers, notifications, clock):
        self.monitors = monitors
        self.providers = providers
        self.notifications = notifications
        self.clock = clock

    def _query_options(self, monitor, now):
        options = deepcopy(monitor['options'])
        if monitor['category'] == 'knps':
            options['dates'] = knps_target_dates(
                options, today=now.astimezone(KST).date())
        return options

    def run(self, *, is_test=False, allow_knps=True):
        summary = CheckSummary()
        cache = {}
        try:
            monitors = self.monitors.list(active_only=True)
        except Exception:
            summary.errors.append('Unable to load monitors')
            return summary
        for monitor in monitors:
            summary.checked += 1
            now = self.clock()
            if is_quiet_time(monitor, now):
                summary.skipped_quiet += 1
                continue
            category = monitor.get('category')
            if category == 'knps' and not allow_knps:
                continue
            provider = self.providers.get(category)
            if provider is None:
                summary.errors.append(f"Monitor {monitor.get('id')} has unsupported category")
                continue
            options = self._query_options(monitor, now)
            key = query_cache_key(category, options)
            try:
                if key not in cache:
                    cache[key] = provider.fetch(options)
                result = cache[key]
            except Exception as exc:
                summary.errors.append(
                    f"Monitor {monitor.get('id')} query failed ({type(exc).__name__})")
                continue
            if result.errors:
                summary.errors.extend(
                    f"Monitor {monitor.get('id')}: {error}" for error in result.errors)
            summary.available += len(result.items)
            outcome = self.notifications.notify(monitor, result.items, is_test=is_test)
            summary.notified += outcome.notified
            summary.messages += outcome.messages
            summary.skipped_quiet += int(outcome.skipped_quiet)
            summary.errors.extend(outcome.errors)
        return summary
