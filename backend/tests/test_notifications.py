from domain.models import Availability, DeliveryBatch, HistoryKey
from notifications.formatters import build_batches
from notifications.telegram import TelegramSender


def item(category='ktx', index=1, **details):
    base = {
        'date': '20991001', 'departure': '서울', 'arrival': '부산',
        'train_no': f'{index:03}', 'departure_time': '090000',
        'arrival_time': '120000', 'seat_class': 'general',
    }
    base.update(details)
    return Availability(category, HistoryKey('20991001', 'target', str(index)), base)


def monitor(category='ktx', **overrides):
    value = {
        'id': 7, 'category': category, 'name': '추석 연휴',
        'telegram_bot_token': 'secret-token', 'telegram_chat_id': '1234',
    }
    value.update(overrides)
    return value


def test_ktx_batches_are_grouped_and_label_standing():
    items = tuple(item(index=i, seat_class='standing' if i == 1 else 'general')
                  for i in range(1, 22))
    batches = build_batches(monitor(), items)

    assert [len(batch.items) for batch in batches] == [20, 1]
    assert all(len(batch.text) <= 4096 for batch in batches)
    assert '입석 예약 가능' in batches[0].text
    assert '추석 연휴' in batches[0].text
    assert '코레일' in batches[0].text


def test_knps_and_parking_use_readable_messages_and_links():
    knps = item('knps', park_name='설악산', campsite_name='야영장',
                facility_type='자동차야영장', available_count=2, waiting_count=0)
    waiting = item('knps', index=2, park_name='설악산', campsite_name='야영장',
                   facility_type='자동차야영장', available_count=0, waiting_count=1)
    parking = item('moduparking', lot_name='시청 주차장', ticket_name='월정기권',
                   price=120000, url='https://example.test/buy')

    assert '예약 2' in build_batches(monitor('knps'), (knps,))[0].text
    assert '대기 1' in build_batches(monitor('knps'), (waiting,))[0].text
    assert 'https://example.test/buy' in build_batches(monitor('moduparking'), (parking,))[0].text


def test_formatter_marks_test_messages():
    batches = build_batches(monitor(), (item(),), is_test=True)
    assert batches[0].text.startswith('[TEST]')


class Response:
    def __init__(self, payload=None, status_error=None):
        self.payload = payload
        self.status_error = status_error

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class Session:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


def batch(**overrides):
    values = {
        'monitor_id': 7, 'category': 'ktx', 'bot_token': 'secret-token',
        'chat_id': '1234', 'text': 'message', 'items': (item(),),
    }
    values.update(overrides)
    return DeliveryBatch(**values)


def test_telegram_sender_requires_credentials_and_items():
    session = Session(Response({'ok': True}))
    sender = TelegramSender(session=session)
    assert not sender.send(batch(bot_token='')).delivered
    assert not sender.send(batch(items=())).delivered
    assert session.calls == []


def test_telegram_sender_checks_http_and_telegram_payload():
    success = Session(Response({'ok': True}))
    assert TelegramSender(session=success).send(batch()).delivered
    assert success.calls[0][1]['timeout'] == 10

    api_failure = TelegramSender(session=Session(Response({'ok': False}))).send(batch())
    invalid_json = TelegramSender(session=Session(Response(ValueError('bad')))).send(batch())
    timeout = TelegramSender(session=Session(error=TimeoutError('slow'))).send(batch())
    assert not api_failure.delivered
    assert not invalid_json.delivered
    assert not timeout.delivered


def test_telegram_error_log_never_contains_credentials(caplog):
    sender = TelegramSender(session=Session(error=RuntimeError('request failed')))
    sender.send(batch())
    assert 'secret-token' not in caplog.text
    assert '1234' not in caplog.text
