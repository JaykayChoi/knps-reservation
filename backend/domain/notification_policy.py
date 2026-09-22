from datetime import datetime, time

from domain.clock import KST, require_aware


def _parse_time(value: str) -> time:
    try:
        return time.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError('quiet hours must use HH:MM') from None


def is_quiet_time(monitor: dict, now: datetime) -> bool:
    if not monitor.get('quiet_hours_enabled', False):
        return False
    current = require_aware(now).astimezone(KST).time().replace(second=0, microsecond=0)
    start = _parse_time(monitor['quiet_hours_start'])
    end = _parse_time(monitor['quiet_hours_end'])
    if start < end:
        return start <= current < end
    return current >= start or current < end
