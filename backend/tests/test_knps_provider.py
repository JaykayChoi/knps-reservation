from unittest.mock import MagicMock, patch

import pytest

from providers.knps import KnpsError, fetch_reservations


def session_with(payload):
    session = MagicMock()
    session.post.return_value.json.return_value = payload
    return session


@patch('providers.knps._build_session')
def test_fetch_reservations_filters_and_normalizes_counts(build):
    build.return_value = session_with({'list': [
        {'officeNm': '덕유산', 'deptNm': '덕유산야영장', 'prdCtgNm': '카라반', 'cntN': 5},
        {'officeNm': '가야산', 'deptNm': '백운동', 'prdCtgNm': '자동차야영장', 'cntN': 0, 'cntW': 2},
    ]})
    rows = fetch_reservations(['20260301'], ['카라반'], ['덕유산'])
    assert rows == [{'date': '20260301', 'park_name': '덕유산',
                     'campsite_name': '덕유산야영장', 'facility_type': '카라반',
                     'available_count': 5, 'waiting_count': 0}]


@patch('providers.knps._build_session')
def test_null_result_and_request_error_are_not_empty_success(build):
    build.return_value = session_with({'list': None})
    with pytest.raises(KnpsError, match='no data'):
        fetch_reservations(['20260301'], [], [])

    broken = MagicMock(); broken.post.side_effect = RuntimeError('network')
    build.return_value = broken
    with pytest.raises(KnpsError, match='1 date'):
        fetch_reservations(['20260301'], [], [])
