"""Validation and canonical storage for category-specific settings."""
from datetime import datetime
import re

CATEGORIES = ('knps', 'moduparking', 'ktx')
FIELDS = {'name', 'category', 'is_active', 'include_waiting', 'date_mode', 'weeks_ahead',
          'selected_days', 'start_date', 'end_date', 'selected_types', 'selected_parks',
          'selected_parkinglots', 'cooldown_days', 'telegram_bot_token', 'telegram_chat_id',
          'ktx_options'}


def normalize_settings(data, existing=None):
    if not isinstance(data, dict):
        raise ValueError('Settings must be an object')
    if set(data) - FIELDS:
        raise ValueError('Unknown settings fields')
    result = {k: v for k, v in (existing or {}).items() if k in FIELDS}
    result.update(data)
    category = result.setdefault('category', 'knps')
    if category not in CATEGORIES:
        raise ValueError('category must be knps, moduparking or ktx')
    cooldown = result.setdefault('cooldown_days', 3)
    if type(cooldown) is not int or not 0 <= cooldown <= 30:
        raise ValueError('cooldown_days must be an integer from 0 to 30')
    for field in ('is_active', 'include_waiting'):
        if field in result and type(result[field]) is not bool:
            raise ValueError(f'{field} must be a boolean')
    for field in ('selected_days', 'selected_types', 'selected_parks', 'selected_parkinglots'):
        value = result.setdefault(field, [])
        if not isinstance(value, list) or any(not isinstance(v, (str, int)) for v in value):
            raise ValueError(f'{field} must be an array')
    if category != 'knps':
        result.update(selected_parks=[], selected_types=[], selected_days=[], weeks_ahead=0,
                      start_date=None, end_date=None, include_waiting=False, date_mode='weekday')
    else:
        for field in ('start_date', 'end_date'):
            result[field] = result.get(field) or None
        mode = result.setdefault('date_mode', 'weekday')
        if mode not in ('weekday', 'absolute'):
            raise ValueError('date_mode must be weekday or absolute')
        weeks = result.setdefault('weeks_ahead', 8)
        if type(weeks) is not int or not 0 <= weeks <= 52:
            raise ValueError('weeks_ahead must be an integer from 0 to 52')
        start, end = result['start_date'], result['end_date']
        if mode == 'absolute' or start or end:
            try:
                sd = datetime.strptime(start, '%Y-%m-%d')
                ed = datetime.strptime(end, '%Y-%m-%d')
            except (TypeError, ValueError):
                raise ValueError('Provide valid start_date and end_date (YYYY-MM-DD)') from None
            if sd > ed:
                raise ValueError('end_date must not precede start_date')
    if category != 'moduparking':
        result['selected_parkinglots'] = []
    if category != 'ktx':
        result['ktx_options'] = {}
    else:
        options = result.get('ktx_options')
        required = {'departure', 'arrival', 'date', 'start_time', 'end_time'}
        station_codes = {'departure_code', 'arrival_code'}
        seat_fields = {'seat_class', 'seat_classes'}
        if (not isinstance(options, dict) or not required.issubset(options)
                or set(options) - required - station_codes - seat_fields
                or not seat_fields.intersection(options)):
            raise ValueError('KTX requires departure, arrival, date, times and seat classes')
        if bool(station_codes & set(options)) and not station_codes.issubset(options):
            raise ValueError('KTX departure and arrival station codes must be provided together')
        options = dict(options)
        for field in required | (station_codes & set(options)) | ({'seat_class'} & set(options)):
            if not isinstance(options[field], str):
                raise ValueError(f'KTX {field} must be text')
            options[field] = options[field].strip()
        allowed_seats = {'general', 'special', 'standing'}
        if 'seat_classes' in options:
            seats = options['seat_classes']
            if (not isinstance(seats, list) or not seats
                    or any(not isinstance(seat, str) or seat not in allowed_seats for seat in seats)):
                raise ValueError('KTX seat_classes must select general, special or standing')
            seats = list(dict.fromkeys(seats))
        else:
            legacy = options['seat_class']
            legacy_seats = {'general': ['general'], 'special': ['special'],
                            'either': ['general', 'special']}
            if legacy not in legacy_seats:
                raise ValueError('KTX seat_class must be general, special or either')
            seats = legacy_seats[legacy]
        options['seat_classes'] = seats
        options.pop('seat_class', None)
        for field in station_codes & set(options):
            if not re.fullmatch(r'\d{4}', options[field]):
                raise ValueError('KTX station codes must contain four digits')
        for field in ('departure', 'arrival'):
            if not re.fullmatch(r'[가-힣A-Za-z0-9() ·-]{1,40}', options[field]):
                raise ValueError('Enter a valid KTX station name (without 역)')
        if options['departure'] == options['arrival']:
            raise ValueError('KTX departure and arrival must differ')
        try:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', options['date']):
                raise ValueError()
            datetime.strptime(options['date'], '%Y-%m-%d')
            for field in ('start_time', 'end_time'):
                if not re.fullmatch(r'\d{2}:\d{2}', options[field]):
                    raise ValueError()
                datetime.strptime(options[field], '%H:%M')
        except ValueError:
            raise ValueError('KTX requires a valid YYYY-MM-DD date and HH:MM times') from None
        if options['start_time'] > options['end_time']:
            raise ValueError('KTX end time must not precede start time')
        result['ktx_options'] = options
    return result
