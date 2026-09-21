"""Anonymous, read-only KTX seat and official station queries."""
from datetime import datetime, timedelta, timezone
import logging

import requests

logger = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))
STATIONS_URL = 'https://www.korail.com/public/st_info/station_data.json'


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
    # korail2 otherwise shares a class-level session. Override before __init__.
    client = Korail.__new__(Korail)
    client._session = TimeoutSession()
    try:
        Korail.__init__(client, '', '', auto_login=False, want_feedback=False)
        return client
    except Exception:
        client._session.close()
        raise KtxError('Could not initialize anonymous KTX lookup') from None


def fetch_stations(*, session=None):
    """Return the station data used by Korail's public station picker."""
    owned = session is None
    session = session or TimeoutSession()
    try:
        response = session.get(STATIONS_URL)
        response.raise_for_status()
        raw = response.json().get('stns', {}).get('stn', [])
        stations = []
        for station in raw:
            code, name = station.get('stn_cd'), station.get('stn_nm')
            if not code or not name:
                continue
            major = station.get('major')
            stations.append({
                'code': str(code),
                'name': str(name),
                'area': str(station.get('area', 'all')),
                'major': int(major) if str(major).isdigit() else None,
            })
        return stations
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        logger.exception('Could not load Korail station data')
        raise KtxError('Could not load Korail station list') from None
    finally:
        if owned:
            session.close()


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
