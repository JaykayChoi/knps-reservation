from dataclasses import dataclass, field

from domain.notification_policy import is_quiet_time
from notifications.formatters import build_batches


@dataclass
class NotificationOutcome:
    notified: int = 0
    messages: int = 0
    skipped_quiet: bool = False
    errors: list[str] = field(default_factory=list)


class NotificationService:
    SNAPSHOT_FIELDS = (
        'category', 'options', 'cooldown_days',
        'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end',
        'telegram_bot_token', 'telegram_chat_id',
    )

    def __init__(self, monitors, history, sender, clock):
        self.monitors = monitors
        self.history = history
        self.sender = sender
        self.clock = clock

    def _still_current(self, original, latest, now):
        if not latest or not latest.get('is_active', False):
            return False, False
        if is_quiet_time(latest, now):
            return False, True
        unchanged = all(latest.get(field) == original.get(field)
                        for field in self.SNAPSHOT_FIELDS)
        return unchanged, False

    def notify(self, monitor, items, *, is_test=False):
        outcome = NotificationOutcome()
        now = self.clock()
        if is_quiet_time(monitor, now):
            outcome.skipped_quiet = True
            return outcome
        if not monitor.get('telegram_bot_token') or not monitor.get('telegram_chat_id'):
            outcome.errors.append(f"Monitor {monitor.get('id')} has no Telegram channel")
            return outcome

        eligible = []
        cooldown = monitor.get('cooldown_days', 3)
        for item in items:
            if is_test or cooldown <= 0:
                eligible.append(item)
                continue
            try:
                if not self.history.is_on_cooldown(
                        monitor['id'], item.history, cooldown, now):
                    eligible.append(item)
            except Exception:
                outcome.errors.append(f"Monitor {monitor['id']} cooldown lookup failed")

        for batch in build_batches(monitor, eligible, is_test=is_test):
            try:
                latest = self.monitors.get(monitor['id'])
            except Exception:
                outcome.errors.append(f"Monitor {monitor['id']} refresh failed")
                break
            current, quiet = self._still_current(monitor, latest, self.clock())
            if quiet:
                outcome.skipped_quiet = True
            if not current:
                break
            result = self.sender.send(batch)
            if not result.delivered:
                outcome.errors.append(result.error or f"Monitor {monitor['id']} delivery failed")
                continue
            outcome.notified += len(batch.items)
            outcome.messages += 1
            if not is_test and cooldown > 0:
                try:
                    self.history.record_batch(
                        monitor['id'], [item.history for item in batch.items], self.clock())
                except Exception:
                    outcome.errors.append(f"Monitor {monitor['id']} history write failed")
        return outcome
