"""Compatibility adapter for the pre-options settings payload."""
from copy import deepcopy

LEGACY_FIELDS = {
    'date_mode', 'weeks_ahead', 'selected_days', 'start_date', 'end_date',
    'selected_types', 'selected_parks', 'selected_parkinglots',
    'include_waiting', 'ktx_options',
}


def legacy_to_canonical(payload):
    if not isinstance(payload, dict):
        raise ValueError('Settings must be an object')
    result = deepcopy(payload)
    present = LEGACY_FIELDS & set(result)
    if 'options' in result and present:
        raise ValueError('Do not send both canonical and legacy options')
    if not present:
        return result
    category = result.get('category', 'knps')
    if category == 'ktx':
        options = deepcopy(result.pop('ktx_options', None))
        if not isinstance(options, dict):
            raise ValueError('KTX options are required')
        if 'seat_classes' not in options:
            mapping = {'general': ['general'], 'special': ['special'],
                       'either': ['general', 'special']}
            seats = mapping.get(options.pop('seat_class', None))
            if seats is None:
                raise ValueError('KTX seat classes are required')
            options['seat_classes'] = seats
    elif category == 'moduparking':
        options = {'lot_ids': result.pop('selected_parkinglots', [])}
    else:
        options = {
            'date_mode': result.pop('date_mode', 'weekday'),
            'weeks_ahead': result.pop('weeks_ahead', 8),
            'days': result.pop('selected_days', ['Fri', 'Sat', 'Sun']),
            'start_date': result.pop('start_date', None) or None,
            'end_date': result.pop('end_date', None) or None,
            'parks': result.pop('selected_parks', []),
            'facility_types': result.pop('selected_types', []),
            'include_waiting': result.pop('include_waiting', True),
        }
    for field in LEGACY_FIELDS:
        result.pop(field, None)
    result['options'] = options
    return result
