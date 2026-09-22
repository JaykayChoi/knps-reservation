from datetime import timedelta, timezone

from domain.clock import require_aware


class HistoryRepository:
    TABLE = 'notification_history'

    def __init__(self, client):
        self.client = client

    def is_on_cooldown(self, monitor_id, key, cooldown_days, now):
        if cooldown_days <= 0:
            return False
        cutoff = require_aware(now).astimezone(timezone.utc) - timedelta(days=cooldown_days)
        response = (self.client.table(self.TABLE).select('id')
                    .eq('monitor_id', monitor_id)
                    .eq('target_date', key.target_date)
                    .eq('target_key', key.target_key)
                    .eq('item_key', key.item_key)
                    .eq('is_waiting', key.is_waiting)
                    .gt('sent_at', cutoff.isoformat()).execute())
        return bool(response.data)

    def record_batch(self, monitor_id, keys, sent_at):
        sent_at = require_aware(sent_at)
        rows = [{
            'monitor_id': monitor_id,
            'target_date': key.target_date,
            'target_key': key.target_key,
            'item_key': key.item_key,
            'is_waiting': key.is_waiting,
            'sent_at': sent_at.astimezone(timezone.utc).isoformat(),
        } for key in keys]
        if rows:
            self.client.table(self.TABLE).insert(rows).execute()

    def delete_for_monitor(self, monitor_id):
        self.client.table(self.TABLE).delete().eq('monitor_id', monitor_id).execute()

    def delete_all(self):
        self.client.table(self.TABLE).delete().neq('id', -1).execute()

    def delete_older_than(self, cutoff):
        cutoff = require_aware(cutoff)
        self.client.table(self.TABLE).delete().lt(
            'sent_at', cutoff.astimezone(timezone.utc).isoformat()).execute()

    def reset_for_kst_day(self):
        return bool(self.client.rpc('reset_notification_history_for_kst_day').execute().data)
