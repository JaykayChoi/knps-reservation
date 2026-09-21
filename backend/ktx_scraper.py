"""Bounded, read-only KTX seat queries using the reference project's client."""
from datetime import datetime, timedelta, timezone
import logging
import os

import requests

logger = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))


class KtxError(RuntimeError):
    pass


class TimeoutSession(requests.Session):
    def request(self, method, url, **kwargs):
        kwargs.setdefault('timeout', (5, 15))
        response = super().request(method, url, **kwargs)
        response.raise_for_status()
        return response


def create_client():
    from korail2 import Korail
    username = os.environ.get('KORAIL_ID')
    password = os.environ.get('KORAIL_PASSWORD')
    if not username or not password:
        raise KtxError('Configure KORAIL_ID and KORAIL_PASSWORD on the server')
    # korail2 otherwise shares a class-level session. Override before __init__.
    client = Korail.__new__(Korail)
    client._session = TimeoutSession()
    try:
        Korail.__init__(client, username, password, auto_login=False, want_feedback=False)
        if not client.login():
            raise KtxError('KTX login failed')
        return client
    except Exception:
        client._session.close()
        raise KtxError('KTX login failed; check server credentials and Korail availability') from None


def fetch_availability(options, *, client=None):
    from korail2 import NoResultsError, TrainType
    now = datetime.now(KST)
    date = options['date'].replace('-', '')
    cursor = options['start_time'].replace(':', '') + '00'
    end = options['end_time'].replace(':', '') + '59'
    if date < now.strftime('%Y%m%d'):
        return []
    if date == now.strftime('%Y%m%d'):
        cursor = max(cursor, now.strftime('%H%M%S'))
    if cursor > end:
        return []
    owned = client is None
    rows, seen = [], set()
    try:
        if owned:
            client = create_client()
        # A safety ceiling prevents a broken upstream cursor from looping forever.
        for _ in range(40):
            try:
                trains = client.search_train(options['departure'], options['arrival'],
                    date=date, time=cursor, train_type=TrainType.KTX, include_no_seats=True)
            except NoResultsError:
                break
            if not trains:
                break
            latest = max(t.dep_time for t in trains)
            for train in trains:
                if train.dep_date != date or not cursor <= train.dep_time <= end:
                    continue
                for seat_class, available in [('general', train.has_general_seat()),
                                               ('special', train.has_special_seat())]:
                    if not available or options['seat_class'] not in (seat_class, 'either'):
                        continue
                    key = (train.train_no, train.dep_time, seat_class)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(dict(date=date, train_no=train.train_no,
                        departure=train.dep_name, arrival=train.arr_name,
                        departure_time=train.dep_time, arrival_time=train.arr_time,
                        seat_class=seat_class))
            if latest >= end:
                break
            if latest < cursor:
                raise KtxError('KTX pagination did not advance')
            next_time = datetime.strptime(date + latest, '%Y%m%d%H%M%S') + timedelta(seconds=1)
            if next_time.strftime('%Y%m%d') != date:
                break
            cursor = next_time.strftime('%H%M%S')
        else:
            raise KtxError('KTX query exceeded page limit; narrow the time window')
        return rows
    except KtxError:
        raise
    except Exception as exc:
        # Upstream exceptions can contain credentials or full request URLs.
        logger.error('KTX lookup failed (%s)', type(exc).__name__)
        raise KtxError('KTX lookup failed; check station names and Korail availability') from None
    finally:
        if owned and client is not None:
            client._session.close()
