class MonitorNotFound(LookupError):
    pass


class MonitorRepository:
    TABLE = 'monitor_settings'

    def __init__(self, client):
        self.client = client

    def list(self, *, active_only=False):
        query = self.client.table(self.TABLE).select('*')
        if active_only:
            query = query.eq('is_active', True)
        return query.order('created_at').execute().data or []

    def get(self, monitor_id):
        rows = (self.client.table(self.TABLE).select('*')
                .eq('id', monitor_id).limit(1).execute().data or [])
        return rows[0] if rows else None

    def create(self, monitor):
        rows = self.client.rpc('create_monitor', {'p_monitor': monitor}).execute().data or []
        if not rows:
            raise RuntimeError('Monitor creation returned no row')
        return rows[0]

    def update(self, monitor_id, monitor):
        rows = (self.client.table(self.TABLE).update(monitor)
                .eq('id', monitor_id).execute().data or [])
        if not rows:
            raise MonitorNotFound('Monitor not found')
        return rows[0]

    def delete(self, monitor_id):
        rows = (self.client.table(self.TABLE).delete()
                .eq('id', monitor_id).execute().data or [])
        if not rows:
            raise MonitorNotFound('Monitor not found')

