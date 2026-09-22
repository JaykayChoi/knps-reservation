from datetime import timezone

from domain.clock import require_aware


class StatusRepository:
    def __init__(self, client):
        self.client = client

    def record_check(self, checked_at):
        checked_at = require_aware(checked_at)
        self.client.table('system_status').upsert({
            'id': 1,
            'last_check_at': checked_at.astimezone(timezone.utc).isoformat(),
        }).execute()

    def get_last_check(self):
        rows = (self.client.table('system_status').select('last_check_at')
                .eq('id', 1).limit(1).execute().data or [])
        return rows[0]['last_check_at'] if rows else None
