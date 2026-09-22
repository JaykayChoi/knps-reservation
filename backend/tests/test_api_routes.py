from copy import deepcopy
from types import SimpleNamespace

from app import create_app
from repositories.monitors import MonitorNotFound


def canonical(**overrides):
    value = {
        'id': 1, 'name': 'Train', 'category': 'ktx', 'is_active': True,
        'options': {'departure': '서울', 'arrival': '부산', 'date': '2099-10-01',
                    'start_time': '08:00', 'end_time': '18:00',
                    'seat_classes': ['general', 'standing']},
        'cooldown_days': 3, 'quiet_hours_enabled': False,
        'quiet_hours_start': '23:00', 'quiet_hours_end': '07:00',
        'telegram_bot_token': '', 'telegram_chat_id': '',
    }
    value.update(overrides)
    return value


class Monitors:
    def __init__(self):
        self.rows = {1: canonical()}

    def list(self, active_only=False):
        return list(self.rows.values())

    def get(self, monitor_id):
        return deepcopy(self.rows.get(monitor_id))

    def create(self, value):
        value = {'id': 2, **value}
        self.rows[2] = value
        return value

    def update(self, monitor_id, value):
        if monitor_id not in self.rows:
            raise MonitorNotFound()
        self.rows[monitor_id] = {'id': monitor_id, **value}
        return self.rows[monitor_id]

    def delete(self, monitor_id):
        if not self.rows.pop(monitor_id, None):
            raise MonitorNotFound()


class History:
    def delete_for_monitor(self, monitor_id):
        self.deleted = monitor_id

    def delete_all(self):
        self.all_deleted = True


class Catalogs:
    def list(self, category, kind=None):
        return [{'category': category, 'kind': kind, 'entry_key': '12',
                 'label': '주차장', 'metadata': {'geohash': 'abc'}}]


class Runner:
    def __init__(self):
        self.status = 'queued'

    def submit(self, is_test=False):
        self.is_test = is_test
        return self.status


class Maintenance:
    def run(self):
        self.called = True


def client():
    deps = SimpleNamespace(
        monitors=Monitors(), history=History(), catalogs=Catalogs(),
        runner=Runner(), maintenance=Maintenance(),
        station_loader=lambda: [{'code': '0001', 'name': '서울'}],
        search_knps=lambda dates, types, parks: [{'date': dates[0]}],
    )
    return create_app({'TESTING': True}, deps).test_client(), deps


def test_settings_crud_uses_canonical_options_and_partial_update():
    web, deps = client()
    assert web.get('/api/settings/all').status_code == 200
    response = web.put('/api/settings/1', json={'quiet_hours_enabled': True})
    assert response.status_code == 200
    assert response.json['setting']['options']['departure'] == '서울'
    assert response.json['setting']['quiet_hours_enabled'] is True

    invalid = web.put('/api/settings/1', json={'unknown': 1})
    missing = web.put('/api/settings/99', json={'name': 'x'})
    assert invalid.status_code == 400
    assert missing.status_code == 404


def test_create_rejects_invalid_json_and_accepts_legacy_boundary():
    web, _ = client()
    assert web.put('/api/settings', json=[]).status_code == 400
    response = web.put('/api/settings', json={
        'name': 'Parking', 'category': 'moduparking',
        'selected_parkinglots': ['12'],
    })
    assert response.status_code == 201
    assert response.json['setting']['options'] == {'lot_ids': ['12']}


def test_check_is_queued_without_blocking_request():
    web, deps = client()
    response = web.post('/api/check?test=true')
    assert response.status_code == 202 and response.json == {'status': 'queued'}
    assert deps.runner.is_test is True
    deps.runner.status = 'running'
    assert web.post('/api/check').status_code == 200


def test_search_validates_dates_and_distinguishes_upstream_failure():
    web, deps = client()
    assert web.get('/api/search').status_code == 400
    assert web.get('/api/search?dates=bad').status_code == 400
    assert web.get('/api/search?dates=2099-10-01').json == [{'date': '20991001'}]
    deps.search_knps = lambda *_: (_ for _ in ()).throw(RuntimeError('secret'))
    failed = web.get('/api/search?dates=2099-10-01')
    assert failed.status_code == 502 and 'secret' not in failed.json['error']


def test_catalog_compatibility_routes_and_removed_ktx_status():
    web, _ = client()
    assert web.get('/api/parking-lots').json == [
        {'seq': '12', 'name': '주차장', 'geohash': 'abc'}]
    assert web.get('/api/ktx/stations').json == [{'code': '0001', 'name': '서울'}]
    assert web.get('/api/ktx/status').status_code == 404
