from datetime import date

from flask import Blueprint, current_app, jsonify, request

blueprint = Blueprint('search', __name__)


def _csv(name):
    return [item.strip() for item in request.args.get(name, '').split(',') if item.strip()]


@blueprint.get('/api/search')
def search():
    raw_dates = _csv('dates') or _csv('date')
    if not raw_dates or len(raw_dates) > 120:
        return jsonify({'error': 'Provide 1 to 120 dates'}), 400
    try:
        dates = [date.fromisoformat(value).strftime('%Y%m%d')
                 if '-' in value else date.fromisoformat(
                     f'{value[:4]}-{value[4:6]}-{value[6:8]}').strftime('%Y%m%d')
                 for value in raw_dates]
    except (ValueError, TypeError):
        return jsonify({'error': 'Dates must use YYYY-MM-DD or YYYYMMDD'}), 400
    try:
        rows = current_app.extensions['dependencies'].search_knps(
            dates, _csv('types'), _csv('parks'))
        return jsonify(rows)
    except Exception:
        current_app.logger.exception('KNPS search failed')
        return jsonify({'error': 'Availability provider failed'}), 502


@blueprint.get('/api/catalogs/<category>')
def catalog(category):
    kind = request.args.get('kind')
    return jsonify(current_app.extensions['dependencies'].catalogs.list(category, kind))


@blueprint.get('/api/parking-lots')
def parking_lots():
    rows = current_app.extensions['dependencies'].catalogs.list('moduparking', 'parking_lot')
    return jsonify([{'seq': row['entry_key'], 'name': row['label'], **row.get('metadata', {})}
                    for row in rows])


@blueprint.get('/api/ktx/stations')
def stations():
    try:
        return jsonify(current_app.extensions['dependencies'].station_loader())
    except Exception:
        current_app.logger.exception('Could not load Korail station list')
        return jsonify({'error': 'Could not load Korail station list'}), 503
