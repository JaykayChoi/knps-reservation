import json
from unittest.mock import MagicMock, patch

from providers import moduparking

LOTS = [
    {'seq': 109902, 'name': '투루파킹 KT&G타워 주차장', 'geohash': 'wydm77'},
    {'seq': 106112, 'name': '카카오 T 대치사거리 주차장', 'geohash': 'wydm77'},
]
MONTHLY = {'couponSeq': 1, 'couponName': '월정기권', 'couponTypeGroup': 10000,
           'price': 242000, 'isSoldOut': False, 'isOpen': True}
HOURLY = {'couponSeq': 2, 'couponName': '1시간권', 'couponTypeGroup': 0,
          'price': 3000, 'isSoldOut': False, 'isOpen': True}


def response(*, payload=None, text=''):
    value = MagicMock(); value.json.return_value = payload; value.text = text
    return value


@patch('providers.moduparking.requests.get')
def test_monthly_passes_share_geohash_request_and_ignore_hourly(get):
    get.return_value = response(payload={'data': [{'parkinglots': [
        {'parkinglotSeq': 109902, 'tickets': [MONTHLY, HOURLY]},
        {'parkinglotSeq': 106112, 'tickets': [{**MONTHLY, 'couponSeq': 3}]},
    ]}]})
    rows = moduparking.fetch_monthly_passes(LOTS)
    assert get.call_count == 1
    assert [row['lot_seq'] for row in rows] == [109902, 106112]
    assert all(row['is_available'] for row in rows)


@patch('providers.moduparking.requests.get')
def test_missing_pin_falls_back_to_detail_payload(get):
    flight = json.dumps({'tickets': [MONTHLY]}, ensure_ascii=False)
    html = f'<script>self.__next_f.push([1,{json.dumps(flight)}])</script>'
    get.side_effect = [response(payload={'data': [{'parkinglots': []}]}), response(text=html)]
    rows = moduparking.fetch_monthly_passes(LOTS[:1])
    assert len(rows) == 1 and rows[0]['ticket_name'] == '월정기권'


def test_json_array_parser_handles_nested_brackets():
    assert moduparking._extract_json_array(
        '{"tickets":[{"name":"a]b","tags":[1,2]}]}', 'tickets') == [
            {'name': 'a]b', 'tags': [1, 2]}]


@patch('providers.moduparking.requests.get', side_effect=RuntimeError('network'))
def test_network_failure_is_not_reported_as_empty_inventory(_get):
    try:
        moduparking.fetch_monthly_passes(LOTS[:1])
    except moduparking.ModuParkingError:
        pass
    else:
        raise AssertionError('provider failure must be raised')
