"""KTX notification orchestration and a single background job per process."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
import logging

import db
import ktx_scraper
import notifier

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='ktx-check')
_lock = Lock()
_future = None
_status = {'status': 'idle'}


def history_key(item):
    return (item['date'], f"KTX:{item['departure']}→{item['arrival']}",
            f"{item['train_no']}:{item['departure_time']}:{item['seat_class']}", False)


def run_check(settings_list, is_test=False):
    summary = {'settings_checked': 0, 'available': 0, 'notified': 0, 'errors': []}
    cache = {}
    for setting in settings_list:
        if setting.get('category') != 'ktx' or not setting.get('is_active', True):
            continue
        sid = setting['id']
        summary['settings_checked'] += 1
        try:
            token, chat = setting.get('telegram_bot_token'), setting.get('telegram_chat_id')
            if not token or not chat:
                raise ktx_scraper.KtxError('Telegram configuration is missing')
            options = setting['ktx_options']
            key = tuple(sorted(options.items()))
            if key not in cache:
                cache[key] = ktx_scraper.fetch_availability(options)
            available = cache[key]
            summary['available'] += len(available)
            cooldown = setting.get('cooldown_days', 3)
            for item in available:
                identity = history_key(item)
                if db.check_cooldown(sid, *identity, cooldown):
                    continue
                if not notifier.send_ktx_notification(token, chat, [item], is_test=is_test):
                    raise ktx_scraper.KtxError('Telegram delivery failed')
                summary['notified'] += 1
                if cooldown > 0:
                    db.record_notification(sid, *identity)
        except Exception as exc:
            message = str(exc) if isinstance(exc, ktx_scraper.KtxError) else 'KTX check failed'
            logger.error('KTX setting %s failed (%s)', sid, type(exc).__name__)
            summary['errors'].append({'setting_id': sid, 'error': message})
    return summary


def _run_job(settings, is_test):
    global _status
    try:
        db.save_ktx_status({'status': 'running', 'started_at': datetime.now(timezone.utc).isoformat()})
        summary = run_check(settings, is_test)
        result = {'status': 'failed' if summary['errors'] else 'completed', **summary}
        db.record_last_check_time()
    except Exception as exc:
        logger.error('KTX job failed (%s)', type(exc).__name__)
        result = {'status': 'failed', 'error': 'KTX background check failed'}
    with _lock:
        _status = {**result, 'finished_at': datetime.now(timezone.utc).isoformat()}
    try:
        db.save_ktx_status(_status)
    except Exception as exc:
        logger.error('Could not persist KTX job status (%s)', type(exc).__name__)
        with _lock:
            _status = {**_status, 'status': 'failed', 'error': 'Could not persist KTX job status',
                       'persistence_error': True}


def submit_check(settings, is_test=False):
    global _future, _status
    watchers = [s for s in settings if s.get('category') == 'ktx' and s.get('is_active', True)]
    if not watchers:
        return {'status': 'no_active_settings'}
    with _lock:
        if _future is not None and not _future.done():
            return {'status': 'running'}
        _status = {'status': 'running', 'started_at': datetime.now(timezone.utc).isoformat()}
        _future = _executor.submit(_run_job, deepcopy(watchers), is_test)
        return {'status': 'queued'}


def get_status():
    # Submission precedes the first database write; never show the previous
    # terminal result while this process has a new job queued/running.
    with _lock:
        if (_future is not None and not _future.done()) or _status.get('persistence_error'):
            return deepcopy(_status)
    return db.get_ktx_status()
