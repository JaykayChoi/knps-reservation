import pytest

from settings_model import normalize_settings


def test_switch_to_parking_clears_knps():
    result = normalize_settings({'category': 'moduparking', 'selected_parkinglots': ['12']},
                                {'category': 'knps', 'selected_parks': ['Park'], 'selected_types': ['Camp']})
    assert result['selected_parks'] == result['selected_types'] == []
    assert result['ktx_options'] == {}


def test_partial_update_preserves_category():
    result = normalize_settings({'is_active': False}, {'category': 'moduparking', 'selected_parkinglots': ['12']})
    assert result['category'] == 'moduparking'
    assert result['selected_parkinglots'] == ['12']


@pytest.mark.parametrize('data', [None, [], {'category': 'invalid'}, {'category': 'ktx'},
                                     {'category': 'knps', 'cooldown_days': -1}])
def test_invalid_settings(data):
    with pytest.raises(ValueError):
        normalize_settings(data)


def test_ktx_validation():
    options = dict(departure='서울', arrival='부산', date='2026-10-01',
                   start_time='08:00', end_time='18:00', seat_class='either')
    assert normalize_settings({'category': 'ktx', 'ktx_options': options})['ktx_options'] == options
    for changes in ({'arrival': '서울'}, {'date': '2026-02-30'}, {'end_time': '07:00'},
                    {'seat_class': 'standing'}, {'start_time': '25:00'}):
        with pytest.raises(ValueError):
            normalize_settings({'category': 'ktx', 'ktx_options': {**options, **changes}})


@pytest.mark.parametrize('data', [None, [], 'bad'])
def test_create_invalid_json_shape_is_400(mocker, data):
    from app import app
    from unittest.mock import Mock
    client = Mock()
    client.table().select().execute.return_value.data = []
    mocker.patch('db.get_supabase', return_value=client)
    response = app.test_client().put('/api/settings', json=data, content_type='application/json',
                                     data='null' if data is None else None)
    assert response.status_code == 400
    client.table().insert.assert_not_called()


@pytest.mark.parametrize('data', [{'weeks_ahead': 'bad'}, {'date_mode': 'invalid'},
    {'date_mode': 'absolute', 'start_date': '2026-02-30', 'end_date': '2026-03-01'}])
def test_reject_invalid_knps_schedule(data):
    with pytest.raises(ValueError):
        normalize_settings({'category': 'knps', **data})
