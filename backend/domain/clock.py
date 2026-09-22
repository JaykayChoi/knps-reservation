from datetime import datetime, timedelta, timezone

UTC = timezone.utc
KST = timezone(timedelta(hours=9), name='Asia/Seoul')


class Clock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def require_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('datetime must include a timezone')
    return value
