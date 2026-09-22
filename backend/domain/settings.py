"""Canonical monitor validation. Legacy field names belong at the API boundary."""
from copy import deepcopy
from datetime import date, time
import re

CATEGORIES = ('knps', 'moduparking', 'ktx')
WRITE_FIELDS = {
    'name', 'category', 'options', 'is_active', 'cooldown_days',
    'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end',
    'telegram_bot_token', 'telegram_chat_id',
}
DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')


def _text(value, field, *, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError(f'{field} must be text')
    value = value.strip()
    if not allow_empty and not value:
        raise ValueError(f'{field} is required')
    return value


def _string_list(value, field, *, allowed=None, nonempty=False):
    if not isinstance(value, list) or any(not isinstance(item, (str, int)) for item in value):
        raise ValueError(f'{field} must be an array')
    values = list(dict.fromkeys(str(item).strip() for item in value))
    if any(not item for item in values) or (nonempty and not values):
        raise ValueError(f'{field} must not be empty')
    if allowed is not None and any(item not in allowed for item in values):
        raise ValueError(f'{field} contains an invalid value')
    return values


def _iso_date(value, field, *, nullable=False):
    if value in (None, '') and nullable:
        return None
    value = _text(value, field)
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError(f'{field} must use YYYY-MM-DD') from None
    return value


def _hhmm(value, field):
    value = _text(value, field)
    if not re.fullmatch(r'\d{2}:\d{2}(?::00)?', value):
        raise ValueError(f'{field} must use HH:MM')
    try:
        parsed = time.fromisoformat(value)
    except ValueError:
        raise ValueError(f'{field} must use HH:MM') from None
    if parsed.second or parsed.microsecond:
        raise ValueError(f'{field} must use minute precision')
    return parsed.strftime('%H:%M')


def _bool(value, field):
    if type(value) is not bool:
        raise ValueError(f'{field} must be a boolean')
    return value


def _normalize_knps(options):
    allowed = {'date_mode', 'weeks_ahead', 'days', 'start_date', 'end_date',
               'parks', 'facility_types', 'include_waiting'}
    if not isinstance(options, dict) or set(options) - allowed:
        raise ValueError('KNPS options contain unknown fields')
    mode = options.get('date_mode', 'weekday')
    if mode not in ('weekday', 'absolute'):
        raise ValueError('date_mode must be weekday or absolute')
    weeks = options.get('weeks_ahead', 8)
    if type(weeks) is not int or not 0 <= weeks <= 52:
        raise ValueError('weeks_ahead must be an integer from 0 to 52')
    days = _string_list(options.get('days', ['Fri', 'Sat', 'Sun']), 'days', allowed=DAYS,
                        nonempty=mode == 'weekday' and weeks > 0)
    start = _iso_date(options.get('start_date'), 'start_date', nullable=True)
    end = _iso_date(options.get('end_date'), 'end_date', nullable=True)
    if (start is None) != (end is None):
        raise ValueError('start_date and end_date must be provided together')
    if mode == 'absolute' and start is None:
        raise ValueError('absolute date mode requires start_date and end_date')
    if start and start > end:
        raise ValueError('end_date must not precede start_date')
    return {
        'date_mode': mode, 'weeks_ahead': weeks, 'days': days,
        'start_date': start, 'end_date': end,
        'parks': _string_list(options.get('parks', []), 'parks'),
        'facility_types': _string_list(options.get('facility_types', []), 'facility_types'),
        'include_waiting': _bool(options.get('include_waiting', True), 'include_waiting'),
    }


def _normalize_parking(options):
    if not isinstance(options, dict) or set(options) - {'lot_ids'}:
        raise ValueError('Parking options contain unknown fields')
    return {'lot_ids': _string_list(options.get('lot_ids', []), 'lot_ids')}


def _normalize_ktx(options):
    required = {'departure', 'arrival', 'date', 'start_time', 'end_time', 'seat_classes'}
    optional = {'departure_code', 'arrival_code'}
    if not isinstance(options, dict) or not required.issubset(options) or set(options) - required - optional:
        raise ValueError('KTX options require stations, date, times and seat classes')
    result = {field: _text(options[field], field) for field in ('departure', 'arrival')}
    if result['departure'] == result['arrival']:
        raise ValueError('KTX departure and arrival must differ')
    code_fields = optional & set(options)
    if code_fields and code_fields != optional:
        raise ValueError('KTX station codes must be provided together')
    for field in optional:
        if field in options:
            code = _text(options[field], field)
            if not re.fullmatch(r'\d{4}', code):
                raise ValueError('KTX station codes must contain four digits')
            result[field] = code
    result['date'] = _iso_date(options['date'], 'date')
    result['start_time'] = _hhmm(options['start_time'], 'start_time')
    result['end_time'] = _hhmm(options['end_time'], 'end_time')
    if result['start_time'] > result['end_time']:
        raise ValueError('KTX end time must not precede start time')
    seats = _string_list(options['seat_classes'], 'seat_classes',
                         allowed=('general', 'special', 'standing'), nonempty=True)
    order = {'general': 0, 'special': 1, 'standing': 2}
    result['seat_classes'] = sorted(seats, key=order.__getitem__)
    return result


OPTION_NORMALIZERS = {'knps': _normalize_knps, 'moduparking': _normalize_parking,
                      'ktx': _normalize_ktx}


def normalize_monitor(data, existing=None):
    if not isinstance(data, dict):
        raise ValueError('Monitor must be an object')
    unknown = set(data) - WRITE_FIELDS
    if unknown:
        raise ValueError(f'Unknown monitor fields: {", ".join(sorted(unknown))}')
    base = {key: deepcopy(value) for key, value in (existing or {}).items() if key in WRITE_FIELDS}
    old_category = base.get('category')
    base.update(deepcopy(data))
    category = base.get('category', 'knps')
    if category not in CATEGORIES:
        raise ValueError('category must be knps, moduparking or ktx')
    if old_category and category != old_category and 'options' not in data:
        raise ValueError('Changing category requires replacement options')
    if 'options' not in base:
        base['options'] = {} if category != 'knps' else {
            'date_mode': 'weekday', 'weeks_ahead': 8, 'days': ['Fri', 'Sat', 'Sun'],
            'start_date': None, 'end_date': None, 'parks': [], 'facility_types': [],
            'include_waiting': True,
        }
    result = {
        'name': _text(base.get('name', 'New Monitor'), 'name'),
        'category': category,
        'options': OPTION_NORMALIZERS[category](base['options']),
        'is_active': _bool(base.get('is_active', True), 'is_active'),
        'cooldown_days': base.get('cooldown_days', 3),
        'quiet_hours_enabled': _bool(base.get('quiet_hours_enabled', False), 'quiet_hours_enabled'),
        'quiet_hours_start': _hhmm(base.get('quiet_hours_start', '23:00'), 'quiet_hours_start'),
        'quiet_hours_end': _hhmm(base.get('quiet_hours_end', '07:00'), 'quiet_hours_end'),
        'telegram_bot_token': _text(base.get('telegram_bot_token', ''), 'telegram_bot_token', allow_empty=True),
        'telegram_chat_id': _text(base.get('telegram_chat_id', ''), 'telegram_chat_id', allow_empty=True),
    }
    if type(result['cooldown_days']) is not int or not 0 <= result['cooldown_days'] <= 30:
        raise ValueError('cooldown_days must be an integer from 0 to 30')
    if (result['quiet_hours_enabled']
            and result['quiet_hours_start'] == result['quiet_hours_end']):
        raise ValueError('quiet hours start and end must differ')
    return result
