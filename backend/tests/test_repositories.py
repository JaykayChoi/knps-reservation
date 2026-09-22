from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from domain.models import HistoryKey
from repositories.history import HistoryRepository
from repositories.monitors import MonitorRepository


def test_monitor_repository_create_uses_atomic_rpc():
    client = Mock()
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=[{'id': 8}])
    repo = MonitorRepository(client)
    payload = {'name': 'Parking', 'category': 'moduparking', 'options': {'lot_ids': []}}

    assert repo.create(payload) == {'id': 8}
    client.rpc.assert_called_once_with('create_monitor', {'p_monitor': payload})


def test_monitor_repository_update_targets_monitor_table():
    client = Mock()
    client.table.return_value.update.return_value.eq.return_value.execute.return_value = SimpleNamespace(
        data=[{'id': 3}])
    repo = MonitorRepository(client)

    assert repo.update(3, {'name': 'Renamed'}) == {'id': 3}
    client.table.assert_called_once_with('monitor_settings')
    client.table.return_value.update.return_value.eq.assert_called_once_with('id', 3)


def test_history_zero_cooldown_never_touches_database():
    client = Mock()
    repo = HistoryRepository(client)
    key = HistoryKey('20991001', 'KTX:서울→부산', '001:090000:general')

    assert repo.is_on_cooldown(1, key, 0, datetime.now(timezone.utc)) is False
    client.table.assert_not_called()


def test_history_uses_generic_keys_and_aware_utc_cutoff():
    client = Mock()
    query = client.table.return_value.select.return_value
    for _ in range(5):
        query = query.eq.return_value
    query.gt.return_value.execute.return_value = SimpleNamespace(data=[{'id': 1}])
    repo = HistoryRepository(client)
    now = datetime(2026, 9, 22, 0, 0, tzinfo=timezone.utc)
    key = HistoryKey('MONTHLY', '109902', '22453')

    assert repo.is_on_cooldown(2, key, 3, now) is True
    client.table.assert_called_once_with('notification_history')


def test_history_records_a_successful_batch_in_one_insert():
    client = Mock()
    repo = HistoryRepository(client)
    sent_at = datetime(2026, 9, 22, 0, 0, tzinfo=timezone.utc)
    keys = [HistoryKey('20991001', 'Park', 'Camp'),
            HistoryKey('20991002', 'Park', 'Camp', True)]

    repo.record_batch(7, keys, sent_at)

    rows = client.table.return_value.insert.call_args.args[0]
    assert [row['monitor_id'] for row in rows] == [7, 7]
    assert rows[0]['target_key'] == 'Park'
    assert rows[1]['is_waiting'] is True
