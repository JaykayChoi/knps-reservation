from domain.models import Availability, QueryResult
from providers.registry import KnpsProvider, KtxProvider, ModuParkingProvider, query_cache_key


def test_ktx_provider_maps_results_to_generic_availability():
    raw = [{
        'date': '20991001', 'departure': '서울', 'arrival': '부산',
        'train_no': '001', 'departure_time': '090000', 'arrival_time': '120000',
        'seat_class': 'standing',
    }]
    provider = KtxProvider(fetch=lambda options: raw)

    result = provider.fetch({'seat_classes': ['standing']})

    assert isinstance(result, QueryResult)
    item = result.items[0]
    assert isinstance(item, Availability)
    assert item.history.target_key == 'KTX:서울→부산'
    assert item.history.item_key == '001:090000:standing'


def test_parking_provider_uses_ids_and_stable_identity():
    provider = ModuParkingProvider(fetch=lambda lot_ids: [{
        'lot_seq': 109902, 'lot_name': 'Lot', 'ticket_name': 'Monthly',
        'coupon_seq': 42, 'price': 100, 'is_available': True, 'url': 'u',
    }])
    result = provider.fetch({'lot_ids': ['109902']})
    assert result.items[0].history.target_date == 'MONTHLY'
    assert result.items[0].history.target_key == 'Lot'
    assert result.items[0].history.item_key == 'Monthly'


def test_knps_provider_creates_separate_reservation_and_waiting_items():
    provider = KnpsProvider(fetch=lambda dates, types, parks: [{
        'date': '20991001', 'park_name': 'Park', 'campsite_name': 'Site',
        'facility_type': 'Camp', 'available_count': 1, 'waiting_count': 2,
    }])
    result = provider.fetch({
        'dates': ['20991001'], 'facility_types': [], 'parks': [],
        'include_waiting': True,
    })
    assert [item.history.is_waiting for item in result.items] == [False, True]


def test_query_cache_key_handles_lists_and_set_like_seat_classes():
    first = {'departure': '서울', 'seat_classes': ['standing', 'general']}
    second = {'seat_classes': ['general', 'standing'], 'departure': '서울'}
    assert query_cache_key('ktx', first) == query_cache_key('ktx', second)
