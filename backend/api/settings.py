from flask import Blueprint, current_app, jsonify, request

from api.legacy_settings import legacy_to_canonical
from domain.settings import normalize_monitor
from repositories.monitors import MonitorNotFound

blueprint = Blueprint('settings', __name__)
SECRET_FIELDS = ('telegram_bot_token', 'telegram_chat_id')


def _deps():
    return current_app.extensions['dependencies']


def _public_monitor(value):
    result = dict(value)
    result['telegram_configured'] = all(bool(result.get(field)) for field in SECRET_FIELDS)
    for field in SECRET_FIELDS:
        result.pop(field, None)
    return result


@blueprint.get('/api/settings')
def list_active_settings():
    return jsonify([_public_monitor(value)
                    for value in _deps().monitors.list(active_only=True)])


@blueprint.get('/api/settings/all')
def list_all_settings():
    return jsonify([_public_monitor(value) for value in _deps().monitors.list()])


@blueprint.get('/api/settings/<int:monitor_id>')
def get_setting(monitor_id):
    value = _deps().monitors.get(monitor_id)
    return ((jsonify(_public_monitor(value)), 200) if value
            else (jsonify({'error': 'Monitor not found'}), 404))


@blueprint.put('/api/settings')
def create_setting():
    try:
        value = normalize_monitor(legacy_to_canonical(request.get_json(silent=True)))
        created = _deps().monitors.create(value)
        return jsonify({'success': True, 'setting': _public_monitor(created)}), 201
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400


@blueprint.put('/api/settings/<int:monitor_id>')
def update_setting(monitor_id):
    existing = _deps().monitors.get(monitor_id)
    if not existing:
        return jsonify({'error': 'Monitor not found'}), 404
    try:
        changes = legacy_to_canonical(request.get_json(silent=True))
        for field in SECRET_FIELDS:
            if changes.get(field) == '' and existing.get(field):
                changes.pop(field)
        value = normalize_monitor(changes, existing)
        updated = _deps().monitors.update(monitor_id, value)
        return jsonify({'success': True, 'setting': _public_monitor(updated)})
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except MonitorNotFound:
        return jsonify({'error': 'Monitor not found'}), 404


@blueprint.delete('/api/settings/<int:monitor_id>')
def delete_setting(monitor_id):
    try:
        _deps().monitors.delete(monitor_id)
        return jsonify({'success': True})
    except MonitorNotFound:
        return jsonify({'error': 'Monitor not found'}), 404


@blueprint.delete('/api/settings/<int:monitor_id>/history')
def delete_monitor_history(monitor_id):
    _deps().history.delete_for_monitor(monitor_id)
    return jsonify({'success': True})


@blueprint.delete('/api/history')
def delete_history():
    _deps().history.delete_all()
    return jsonify({'success': True})
