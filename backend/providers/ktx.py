"""Anonymous KTX availability through the API used by korail.com ticket search."""
from datetime import datetime, timedelta, timezone
import logging
import random
import string
import time
from urllib.parse import urlsplit

import requests

logger = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))
STATIONS_URL = 'https://www.korail.com/public/st_info/station_data.json'
SCHEDULE_URL = ('https://smart.letskorail.com:443/classes/'
                'com.korail.mobile.seatMovie.ScheduleView')
NO_RESULTS = {'P100', 'WRG000000', 'WRD000061', 'WRT300005'}


class KtxError(RuntimeError):
    pass


class DynaPathSigner:
    """Create the request token required by Korail's public schedule API."""
    TABLE = '3FE9jgRD4KdCyuawklqGJYmvfMn15P7US8XbxeLQtWT6OicBAopINs2Vh0HZrz'

    def __init__(self, started_at=None):
        self.started_at = str(started_at or int(time.time() * 1000))

    @staticmethod
    def _bytes(value):
        result = []
        for character in value:
            code = ord(character)
            if code < 128:
                result.append(code)
            elif code < 2048:
                result.extend((128 | ((code >> 7) & 15), code & 127))
            elif (63488 & code) != 55296:
                result.extend((((code >> 14) & 15) | 144, (code >> 7) & 127, code & 127))
        return result

    @staticmethod
    def _key_number(value):
        result = 0
        for character in value:
            code, bit = ord(character), 32768
            while bit and not bit & code:
                bit >>= 1
            result = result * (bit << 1) + code
        return result

    @classmethod
    def _permutation(cls, number, size):
        result = ''
        for index in range(size):
            remainder = number % (size - index)
            result += [character for character in cls.TABLE if character not in result][remainder]
            number //= size - index
        return result

    @classmethod
    def _encode(cls, value, table):
        values, output = cls._bytes(value), []
        paired = len(values) - len(values) % 2
        for index in range(0, paired, 2):
            number = values[index] * 161 + values[index + 1]
            digits = []
            for _ in range(3):
                digits.append(number % 30); number //= 30
            output.extend(table[digit] for digit in reversed(digits))
        if paired < len(values):
            number = values[-1]
            output.extend((table[number // 30], table[number % 30]))
        return ''.join(output)

    def token(self, *, timestamp=None, nonce=None, device_id='558a4f02041657ea'):
        timestamp = int(timestamp or time.time() * 1000)
        nonce = nonce or ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        dynamic_key = f'v1+{nonce}+{timestamp}'
        key = self._encode(dynamic_key, self.TABLE)
        table = self._permutation(self._key_number(dynamic_key), 30)
        plain = (f'ai=com.korail.talk&di={device_id}&as=%5B38ff229cb34c7dda8e28220a2d750cce%5D&'
                 f'su=false&dbg=false&emu=false&hk=false&it={self.started_at}&ts={timestamp}&rt=0&'
                 'os=13&dm=SM-S928N&st=Android&sv=v1')
        return f'bEeEP{self.TABLE[len(key)]}{key}{self._encode(plain, table)}'


class OfficialKorailClient:
    def __init__(self, session=None, signer=None):
        self.session = session or requests.Session()
        self.signer = signer or DynaPathSigner()

    def search_page(self, departure, arrival, date, departure_time):
        payload = {
            'Device': 'AD', 'Version': '250601002', 'radJobId': '1',
            'selGoTrain': '100', 'txtCardPsgCnt': '0', 'txtGdNo': '',
            'txtGoAbrdDt': date, 'txtGoEnd': arrival, 'txtGoHour': departure_time,
            'txtGoStart': departure, 'txtJobDv': '', 'txtMenuId': '11',
            'txtPsgFlg_1': '1', 'txtPsgFlg_2': '0', 'txtPsgFlg_8': '0',
            'txtPsgFlg_3': '0', 'txtPsgFlg_4': '0', 'txtPsgFlg_5': '0',
            'txtSeatAttCd_2': '000', 'txtSeatAttCd_3': '000',
            'txtSeatAttCd_4': '015', 'txtTrnGpCd': '100',
        }
        response = self.session.post(
            SCHEDULE_URL, params=payload,
            headers={'User-Agent': 'Dalvik/2.1.0 (Linux; Android 13)',
                     'x-dynapath-m-token': self.signer.token()},
            timeout=(5, 15),
        )
        response.raise_for_status()
        data = response.json()
        if data.get('strResult') == 'FAIL':
            if data.get('h_msg_cd') in NO_RESULTS:
                return []
            raise KtxError('Korail rejected the anonymous schedule request')
        rows = data.get('trn_infos', {}).get('trn_info', [])
        if not isinstance(rows, list):
            raise KtxError('Korail returned an invalid schedule response')
        return rows

    def close(self):
        self.session.close()


def fetch_stations(*, session=None):
    owned = session is None
    session = session or requests.Session()
    try:
        response = session.get(STATIONS_URL, timeout=(5, 15))
        response.raise_for_status()
        raw = response.json().get('stns', {}).get('stn', [])
        return [{'code': str(row['stn_cd']), 'name': str(row['stn_nm']),
                 'area': str(row.get('area', 'all')),
                 'major': int(row['major']) if str(row.get('major', '')).isdigit() else None}
                for row in raw if row.get('stn_cd') and row.get('stn_nm')]
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError):
        logger.exception('Could not load Korail station data')
        raise KtxError('Could not load Korail station list') from None
    finally:
        if owned:
            session.close()


def _availability(row, selected):
    classes = []
    if row.get('h_gen_rsv_cd') == '11' and 'general' in selected:
        classes.append('general')
    if row.get('h_spe_rsv_cd') == '11' and 'special' in selected:
        classes.append('special')
    if row.get('h_stnd_rsv_cd') == '11' and 'standing' in selected:
        classes.append('standing')
    return classes


def fetch_availability(options, *, client=None):
    now = datetime.now(KST)
    target_date = options['date'].replace('-', '')
    cursor = options['start_time'].replace(':', '') + '00'
    end = options['end_time'].replace(':', '') + '59'
    if target_date < now.strftime('%Y%m%d'):
        return []
    if target_date == now.strftime('%Y%m%d'):
        cursor = max(cursor, now.strftime('%H%M%S'))
    if cursor > end:
        return []
    selected = set(options['seat_classes'])
    owned = client is None
    client = client or OfficialKorailClient()
    results, seen = [], set()
    try:
        for _ in range(40):
            rows = client.search_page(options['departure'], options['arrival'], target_date, cursor)
            if not rows:
                break
            latest = max(str(row.get('h_dpt_tm', '')) for row in rows)
            for row in rows:
                departure_time = str(row.get('h_dpt_tm', ''))
                if str(row.get('h_dpt_dt')) != target_date or not cursor <= departure_time <= end:
                    continue
                for seat_class in _availability(row, selected):
                    key = (str(row.get('h_trn_no')), departure_time, seat_class)
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append({
                        'date': target_date, 'train_no': key[0],
                        'departure': str(row.get('h_dpt_rs_stn_nm', options['departure'])),
                        'arrival': str(row.get('h_arv_rs_stn_nm', options['arrival'])),
                        'departure_time': departure_time,
                        'arrival_time': str(row.get('h_arv_tm', '')),
                        'seat_class': seat_class,
                    })
            if latest >= end:
                break
            if not latest or latest < cursor:
                raise KtxError('KTX pagination did not advance')
            next_time = datetime.strptime(target_date + latest, '%Y%m%d%H%M%S') + timedelta(seconds=1)
            if next_time.strftime('%Y%m%d') != target_date:
                break
            cursor = next_time.strftime('%H%M%S')
        else:
            raise KtxError('KTX query exceeded page limit; narrow the time window')
        return results
    except KtxError:
        raise
    except requests.HTTPError as exc:
        response = exc.response
        status = response.status_code if response is not None else 'unknown'
        host = urlsplit(response.url).hostname if response is not None else None
        logger.error('KTX lookup failed (HTTP %s from %s)', status, host or 'unknown host')
        raise KtxError('KTX lookup failed; check stations and Korail availability') from None
    except Exception as exc:
        logger.error('KTX lookup failed (%s)', type(exc).__name__)
        raise KtxError('KTX lookup failed; check stations and Korail availability') from None
    finally:
        if owned:
            client.close()
