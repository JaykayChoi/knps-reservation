from collections.abc import Callable

from domain.models import Availability, DeliveryBatch

TELEGRAM_TEXT_LIMIT = 4096


def _date(value):
    value = str(value)
    return f'{value[:4]}-{value[4:6]}-{value[6:8]}' if len(value) == 8 else value


def _time(value):
    value = str(value)
    return f'{value[:2]}:{value[2:4]}' if len(value) >= 4 and ':' not in value else value


def _knps_line(item):
    detail = item.details
    statuses = []
    if detail.get('available_count', 0) > 0:
        statuses.append(f"예약 {detail['available_count']}")
    if detail.get('waiting_count', 0) > 0:
        statuses.append(f"대기 {detail['waiting_count']}")
    status = ' / '.join(statuses) or '만석'
    return (f"📅 {_date(detail.get('date', item.history.target_date))}\n"
            f"📍 {detail.get('park_name', '')} ({detail.get('campsite_name', '')})\n"
            f"⛺ {detail.get('facility_type', '')} - {status}")


def _parking_line(item):
    detail = item.details
    price = detail.get('price')
    price_text = f'{price:,}원' if isinstance(price, (int, float)) else str(price or '')
    return (f"📍 {detail.get('lot_name', '')}\n"
            f"🎫 {detail.get('ticket_name', '')} - {price_text}\n"
            f"{detail.get('url', '')}")


def _ktx_line(item):
    detail = item.details
    seat = {'general': '일반실', 'special': '특실', 'standing': '입석'}.get(
        detail.get('seat_class'), detail.get('seat_class', ''))
    return (f"• KTX {detail.get('train_no', '')} · {_time(detail.get('departure_time', ''))} → "
            f"{_time(detail.get('arrival_time', ''))} · {seat} 예약 가능")


FORMAT = {
    'knps': ('국립공원 빈자리 알림', _knps_line, 30, 'https://reservation.knps.or.kr'),
    'moduparking': ('월정기권 자리 알림', _parking_line, 30, ''),
    'ktx': ('KTX 빈자리 알림', _ktx_line, 20,
            '성인 1명 기준입니다. 코레일에서 현재 좌석을 확인해 주세요.\n'
            'https://www.korail.com/ticket/search/list'),
}


def _header(monitor, category, is_test):
    title = FORMAT[category][0]
    prefix = '[TEST] ' if is_test else ''
    return f"{prefix}[{title}]\n{monitor.get('name', '')}".rstrip()


def _render(header: str, lines: list[str], footer: str, part=None):
    part_text = f'\n({part[0]}/{part[1]})' if part else ''
    sections = [header + part_text, *lines]
    if footer:
        sections.append(footer)
    return '\n\n'.join(sections)


def _split_messages(header: str, items: tuple[Availability, ...],
                    formatter: Callable[[Availability], str], max_items: int, footer: str):
    groups = []
    current_items = []
    current_lines = []
    for item in items:
        line = formatter(item)
        if len(line) > 3000:
            line = line[:2997] + '...'
        proposed = _render(header, current_lines + [line], footer)
        if current_items and (len(current_items) >= max_items or len(proposed) > TELEGRAM_TEXT_LIMIT):
            groups.append((tuple(current_items), current_lines))
            current_items, current_lines = [], []
        current_items.append(item)
        current_lines.append(line)
    if current_items:
        groups.append((tuple(current_items), current_lines))
    total = len(groups)
    return [(group_items, _render(header, lines, footer, (index, total) if total > 1 else None))
            for index, (group_items, lines) in enumerate(groups, 1)]


def build_batches(monitor, items, *, is_test=False):
    items = tuple(items)
    if not items:
        return ()
    category = monitor['category']
    if category not in FORMAT:
        raise ValueError(f'Unsupported notification category: {category}')
    _, formatter, max_items, footer = FORMAT[category]
    groups = _split_messages(_header(monitor, category, is_test), items,
                             formatter, max_items, footer)
    return tuple(DeliveryBatch(
        monitor_id=monitor['id'], category=category,
        bot_token=monitor.get('telegram_bot_token', ''),
        chat_id=monitor.get('telegram_chat_id', ''), text=text, items=group_items,
    ) for group_items, text in groups)
