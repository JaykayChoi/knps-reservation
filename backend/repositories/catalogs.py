class CatalogRepository:
    def __init__(self, client):
        self.client = client

    def list(self, category, kind=None):
        query = (self.client.table('monitor_catalog').select('*')
                 .eq('category', category))
        if kind:
            query = query.eq('kind', kind)
        return query.order('label').execute().data or []
