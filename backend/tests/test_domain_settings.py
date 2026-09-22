from datetime import datetime, timezone

import pytest

from api.legacy_settings import legacy_to_canonical
from domain.notification_policy import is_quiet_time
from domain.schedules import knps_target_dates
from domain.settings import normalize_monitor


def test_quiet_hours_default_off_and_partial_update_preserves_options():
    existing = normalize_monitor({
        'name': 'Morning train',
        'category': 'ktx',
        'options': {
            'departure': '서울', 'arrival': '부산', 'date': '2099-10-01',
            'start_time': '08:00', 'end_time': '18:00',
            'seat_classes': ['special', 'general', 'general'],
        },
    })

    assert existing['quiet_hours_enabled'] is False
    assert existing['quiet_hours_start'] == '23:00'
    assert existing['quiet_hours_end'] == '07:00'
    assert existing['options']['seat_classes'] == ['general', 'special']

    updated = normalize_monitor({'quiet_hours_enabled': True}, existing)
    assert updated['options'] == existing['options']
    assert updated['quiet_hours_enabled'] is True


@pytest.mark.parametrize(('utc_time', 'quiet'), [
    ('2026-09-21T13:59:00+00:00', False),  # 22:59 KST
    ('2026-09-21T14:00:00+00:00', True),   # 23:00 KST
    ('2026-09-21T21:59:00+00:00', True),   # 06:59 KST
    ('2026-09-21T22:00:00+00:00', False),  # 07:00 KST
])
def test_quiet_hours_cross_midnight_uses_kst_and_end_is_exclusive(utc_time, quiet):
    monitor = {'quiet_hours_enabled': True, 'quiet_hours_start': '23:00',
               'quiet_hours_end': '07:00'}
    assert is_quiet_time(monitor, datetime.fromisoformat(utc_time)) is quiet


def test_quiet_hours_reject_equal_times_when_enabled():
    with pytest.raises(ValueError, match='must differ'):
        normalize_monitor({
            'name': 'Quiet', 'category': 'moduparking',
            'options': {'lot_ids': ['12']},
            'quiet_hours_enabled': True,
            'quiet_hours_start': '08:00', 'quiet_hours_end': '08:00',
        })


def test_database_time_values_are_normalized_to_minute_precision():
    value = normalize_monitor({
        'name': 'Quiet', 'category': 'moduparking',
        'options': {'lot_ids': ['12']},
        'quiet_hours_start': '23:00:00', 'quiet_hours_end': '07:00:00',
    })
    assert value['quiet_hours_start'] == '23:00'
    assert value['quiet_hours_end'] == '07:00'


def test_category_change_requires_replacement_options():
    existing = normalize_monitor({
        'name': 'Parking', 'category': 'moduparking',
        'options': {'lot_ids': ['12']},
    })
    with pytest.raises(ValueError, match='options'):
        normalize_monitor({'category': 'ktx'}, existing)


def test_legacy_ktx_and_knps_payloads_are_adapted_at_boundary():
    legacy_ktx = legacy_to_canonical({
        'name': 'Train', 'category': 'ktx',
        'ktx_options': {
            'departure': '서울', 'arrival': '부산', 'date': '2099-10-01',
            'start_time': '08:00', 'end_time': '18:00', 'seat_class': 'either',
        },
    })
    assert legacy_ktx['options']['seat_classes'] == ['general', 'special']
    assert 'ktx_options' not in legacy_ktx

    legacy_knps = legacy_to_canonical({
        'name': 'Camp', 'category': 'knps', 'date_mode': 'weekday',
        'weeks_ahead': 4, 'selected_days': ['Fri'],
        'selected_parks': ['덕유산'], 'selected_types': ['카라반'],
        'include_waiting': False,
    })
    assert legacy_knps['options'] == {
        'date_mode': 'weekday', 'weeks_ahead': 4, 'days': ['Fri'],
        'start_date': None, 'end_date': None, 'parks': ['덕유산'],
        'facility_types': ['카라반'], 'include_waiting': False,
    }


def test_canonical_and_legacy_options_cannot_be_mixed():
    with pytest.raises(ValueError, match='both canonical and legacy'):
        legacy_to_canonical({
            'category': 'moduparking', 'options': {'lot_ids': ['12']},
            'selected_parkinglots': ['12'],
        })


def test_knps_schedule_unions_weekdays_and_inclusive_explicit_range():
    options = {
        'date_mode': 'weekday', 'weeks_ahead': 1, 'days': ['Fri'],
        'start_date': '2026-02-24', 'end_date': '2026-02-25',
    }
    assert knps_target_dates(options, today=datetime(2026, 2, 23, tzinfo=timezone.utc).date()) == [
        '20260224', '20260225', '20260227',
    ]


def test_knps_schedule_limits_explicit_range_to_120_days():
    options = {
        'date_mode': 'absolute', 'weeks_ahead': 0, 'days': [],
        'start_date': '2026-01-01', 'end_date': '2026-12-31',
    }
    dates = knps_target_dates(options, today=datetime(2026, 1, 1, tzinfo=timezone.utc).date())
    assert len(dates) == 120
    assert dates[0] == '20260101'
