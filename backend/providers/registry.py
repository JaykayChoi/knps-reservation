import json

from domain.models import Availability, HistoryKey, QueryResult


def _canonical(value):
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        normalized = [_canonical(item) for item in value]
        return sorted(normalized, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True))
    return value


def query_cache_key(category, options):
    return category, json.dumps(_canonical(options), ensure_ascii=False,
                                sort_keys=True, separators=(',', ':'))


class KnpsProvider:
    category = 'knps'

    def __init__(self, fetch):
        self._fetch = fetch

    def fetch(self, options):
        raw_items = self._fetch(options.get('dates', []),
                                options.get('facility_types', []), options.get('parks', []))
        items = []
        for raw in raw_items:
            if raw.get('available_count', 0) > 0:
                items.append(Availability(self.category, HistoryKey(
                    raw['date'], raw['park_name'], raw['facility_type'], False),
                    {**raw, 'waiting_count': 0}))
            if options.get('include_waiting', True) and raw.get('waiting_count', 0) > 0:
                items.append(Availability(self.category, HistoryKey(
                    raw['date'], raw['park_name'], raw['facility_type'], True),
                    {**raw, 'available_count': 0}))
        return QueryResult(tuple(items))


class ModuParkingProvider:
    category = 'moduparking'

    def __init__(self, fetch, catalog_loader=None):
        self._fetch = fetch
        self._catalog_loader = catalog_loader

    def fetch(self, options):
        lot_ids = set(options.get('lot_ids', []))
        if self._catalog_loader:
            entries = self._catalog_loader('moduparking', 'parking_lot')
            lots = [{
                'seq': int(entry['entry_key']), 'name': entry['label'],
                'geohash': entry.get('metadata', {}).get('geohash', ''),
            } for entry in entries if entry['entry_key'] in lot_ids]
        else:
            lots = sorted(lot_ids)
        raw_items = self._fetch(lots)
        items = [Availability(self.category, HistoryKey(
            'MONTHLY', raw['lot_name'], raw['ticket_name'], False), dict(raw))
            for raw in raw_items if raw.get('is_available')]
        return QueryResult(tuple(items))


class KtxProvider:
    category = 'ktx'

    def __init__(self, fetch):
        self._fetch = fetch

    def fetch(self, options):
        raw_items = self._fetch(options)
        items = [Availability(self.category, HistoryKey(
            raw['date'], f"KTX:{raw['departure']}→{raw['arrival']}",
            f"{raw['train_no']}:{raw['departure_time']}:{raw['seat_class']}", False), dict(raw))
            for raw in raw_items]
        return QueryResult(tuple(items))


def default_registry(catalogs=None):
    from providers import knps, ktx, moduparking
    return {
        'knps': KnpsProvider(knps.fetch_reservations),
        'moduparking': ModuParkingProvider(
            moduparking.fetch_monthly_passes,
            catalogs.list if catalogs is not None else None,
        ),
        'ktx': KtxProvider(ktx.fetch_availability),
    }
