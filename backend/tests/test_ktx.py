from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import ktx_scraper
import ktx_monitor
import notifier


OPTIONS = dict(departure='서울', arrival='부산', date='2099-10-01',
               start_time='08:00', end_time='18:00', seat_class='either')


def train(no='001', time='090000', general=True, special=False):
    return SimpleNamespace(train_no=no, dep_date='20991001', dep_time=time,
                           arr_time='120000', dep_name='서울', arr_name='부산',
                           train_type_name='KTX', has_general_seat=lambda: general,
                           has_special_seat=lambda: special)


def test_paginates_past_sold_out_trains_and_filters_classes():
    client = Mock()
    client.search_train.side_effect = [[train(general=False)],
                                      [train('002', '100000', special=True)], []]
    rows = ktx_scraper.fetch_availability(OPTIONS, client=client)
    assert [r['seat_class'] for r in rows] == ['general', 'special']
    assert client.search_train.call_args_list[1].kwargs['time'] == '090001'
    assert client.search_train.call_args_list[0].kwargs['include_no_seats'] is True


def test_window_and_selected_class():
    client = Mock()
    client.search_train.return_value = [train('1', '080000', special=True), train('2', '180100')]
    rows = ktx_scraper.fetch_availability({**OPTIONS, 'seat_class': 'special'}, client=client)
    assert len(rows) == 1 and rows[0]['seat_class'] == 'special'


def test_upstream_errors_are_not_empty_success():
    client = Mock()
    client.search_train.side_effect = RuntimeError('sensitive upstream text')
    with pytest.raises(ktx_scraper.KtxError, match='KTX lookup failed'):
        ktx_scraper.fetch_availability(OPTIONS, client=client)


def test_expired_date_skips_login(mocker):
    make = mocker.patch('ktx_scraper.create_client')
    assert ktx_scraper.fetch_availability({**OPTIONS, 'date': '2000-01-01'}) == []
    make.assert_not_called()


@pytest.mark.parametrize('sent,cooldown,recorded', [(True, 3, True), (False, 3, False), (True, 0, False)])
def test_notification_records_only_success(mocker, sent, cooldown, recorded):
    item = dict(date='20991001', departure='서울', arrival='부산', train_no='001',
                departure_time='090000', arrival_time='120000', seat_class='general')
    mocker.patch('ktx_monitor.ktx_scraper.fetch_availability', return_value=[item])
    mocker.patch('ktx_monitor.db.check_cooldown', return_value=False)
    record = mocker.patch('ktx_monitor.db.record_notification')
    mocker.patch('ktx_monitor.notifier.send_ktx_notification', return_value=sent)
    summary = ktx_monitor.run_check([dict(id=1, category='ktx', ktx_options=OPTIONS,
        telegram_bot_token='test', telegram_chat_id='test', cooldown_days=cooldown)])
    assert record.called is recorded
    assert summary['notified'] == (1 if sent else 0)
    assert bool(summary['errors']) is (not sent)


def test_cooldown_suppresses_and_distinguishes_train_classes(mocker):
    item = dict(date='20991001', departure='서울', arrival='부산', train_no='001',
                departure_time='090000', arrival_time='120000', seat_class='general')
    mocker.patch('ktx_monitor.ktx_scraper.fetch_availability', return_value=[item])
    mocker.patch('ktx_monitor.db.check_cooldown', return_value=True)
    send = mocker.patch('ktx_monitor.notifier.send_ktx_notification')
    ktx_monitor.run_check([dict(id=1, category='ktx', ktx_options=OPTIONS,
        telegram_bot_token='test', telegram_chat_id='test')])
    send.assert_not_called()
    assert ktx_monitor.history_key(item) != ktx_monitor.history_key({**item, 'seat_class': 'special'})


def test_worker_failure_is_visible(mocker):
    save = mocker.patch('ktx_monitor.db.save_ktx_status')
    mocker.patch('ktx_monitor.run_check', side_effect=RuntimeError('secret'))
    ktx_monitor._run_job([], False)
    status = save.call_args.args[0]
    assert status['status'] == 'failed'
    assert 'secret' not in str(status)


def test_telegram_contains_readable_korean_and_rejects_api_error(mocker):
    post = mocker.patch('notifier.requests.post')
    post.return_value.json.return_value = {'ok': True}
    item = dict(date='20991001', departure='서울', arrival='부산', train_no='001',
                departure_time='090000', arrival_time='120000', seat_class='general')
    assert notifier.send_ktx_notification('test', 'test', [item])
    text = post.call_args.kwargs['json']['text']
    assert '일반실 예약 가능' in text
    assert '서울 → 부산' in text
    post.return_value.json.return_value = {'ok': False}
    assert not notifier.send_ktx_notification('test', 'test', [item])


def test_category_dispatch_runs_before_knps_probability_gate(mocker, monkeypatch):
    import app as routes
    setting = {'id': 1, 'category': 'ktx', 'ktx_options': OPTIONS}
    mocker.patch('app.db.get_settings', return_value=[setting])
    mocker.patch('app.db.truncate_notification_history')
    mocker.patch('app.db.delete_old_notifications')
    mocker.patch('app.db.record_last_check_time')
    submit = mocker.patch('app.ktx_monitor.submit_check', return_value={'status': 'queued'})
    knps = mocker.patch('app.scraper.fetch_reservations')
    parking = mocker.patch('app.modu_scraper.fetch_monthly_passes')
    mocker.patch('app.random.random', return_value=1)
    monkeypatch.setenv('CHECK_PROBABILITY', '0')
    response = routes.app.test_client().get('/api/check')
    assert response.status_code == 200
    assert response.json['ktx']['status'] == 'queued'
    submit.assert_called_once_with([setting], is_test=False)
    knps.assert_not_called()
    parking.assert_not_called()


def test_submit_does_not_duplicate_running_job(mocker):
    future = Mock()
    future.done.return_value = False
    mocker.patch('ktx_monitor._future', future)
    executor = mocker.patch('ktx_monitor._executor')
    assert ktx_monitor.submit_check([{'id': 1, 'category': 'ktx'}]) == {'status': 'running'}
    executor.submit.assert_not_called()


def test_client_uses_isolated_timeouts_without_login_output(mocker, monkeypatch):
    import korail2
    monkeypatch.setenv('KORAIL_ID', 'test')
    monkeypatch.setenv('KORAIL_PASSWORD', 'test')
    mocker.patch.object(korail2.Korail, 'login', return_value=True)
    client = ktx_scraper.create_client()
    assert isinstance(client._session, ktx_scraper.TimeoutSession)
    assert client._session is not korail2.Korail._session
    assert not client.want_feedback
    request = mocker.patch('requests.Session.request')
    client._session.get('https://example.invalid')
    assert request.call_args.kwargs['timeout'] == (5, 15)
    client._session.close()


def test_status_does_not_show_previous_completion_before_worker_persists(mocker):
    future = Mock()
    future.done.return_value = False
    mocker.patch('ktx_monitor._future', future)
    mocker.patch('ktx_monitor._status', {'status': 'running'})
    persisted = mocker.patch('ktx_monitor.db.get_ktx_status', return_value={'status': 'completed'})
    assert ktx_monitor.get_status()['status'] == 'running'
    persisted.assert_not_called()
