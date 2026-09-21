import requests

def send_telegram_notification(token, chat_id, reservations, is_test=False):
    if not token or not chat_id or not reservations:
        return

    # 예약 항목을 30개씩 분할
    chunk_size = 30
    reservation_chunks = [reservations[i:i + chunk_size] for i in range(0, len(reservations), chunk_size)]
    
    success_count = 0
    total_chunks = len(reservation_chunks)
    
    for chunk_index, chunk in enumerate(reservation_chunks):
        header = "[TEST] 🔔" if is_test else "🔔"
        message = f"{header} *[국립공원 빈자리 알림]*\n\n"
        
        # 현재 청크 정보 추가 (여러 청크일 경우)
        if total_chunks > 1:
            message += f"*({chunk_index + 1}/{total_chunks})*\n\n"
        
        for res in chunk:
            date_str = f"{res['date'][:4]}-{res['date'][4:6]}-{res['date'][6:8]}"
            message += f"📅 *{date_str}*\n"
            message += f"📍 {res['park_name']} ({res['campsite_name']})\n"
            status_parts = []
            if res.get('available_count', 0) > 0:
                status_parts.append(f"예약 {res['available_count']}")
            if res.get('waiting_count', 0) > 0:
                status_parts.append(f"대기 {res['waiting_count']}")
            status_str = " / ".join(status_parts) if status_parts else "만석"
            message += f"⛺ {res['facility_type']} - {status_str}\n"
            message += "-------------------\n"
        
        message += "\n[지금 예약하기](https://reservation.knps.or.kr)"

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            success_count += 1
        except Exception as e:
            print(f"Telegram error for chunk {chunk_index + 1}: {e}")
            # 하나의 청크 실패해도 나머지 청크는 시도
            continue

    # 모든 청크가 성공했는지 반환
    return success_count == total_chunks


def send_parking_notification(token, chat_id, passes, is_test=False):
    """모두의주차장 월정기권 판매중 알림을 전송한다.

    passes: modu_scraper.fetch_monthly_passes() 가 돌려주는 항목 리스트.
    """
    if not token or not chat_id or not passes:
        return False

    header = "[TEST] 🅿️" if is_test else "🅿️"
    message = f"{header} *[월정기권 자리 알림]*\n\n"

    for item in passes:
        message += f"📍 *{item['lot_name']}*\n"
        message += f"🎫 {item['ticket_name']} - {item['price']:,}원\n"
        message += f"[구매 페이지 열기]({item['url']})\n"
        message += "-------------------\n"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"Telegram error for parking notification: {e}")
        return False

def send_ktx_notification(token, chat_id, trains, is_test=False):
    """Send a batch as one plain-text message."""
    import logging
    if not token or not chat_id or not trains:
        return False
    first = trains[0]
    date = first['date']
    text = (
        ('[TEST] ' if is_test else '') + '[KTX 빈자리 알림]\n'
        f"{date[:4]}-{date[4:6]}-{date[6:]} {first['departure']} → {first['arrival']}\n"
        f"예약 가능 좌석 {len(trains)}건\n\n"
    )
    for train in trains:
        seat = {'general': '일반실', 'special': '특실', 'standing': '입석'}[train['seat_class']]
        departure = train['departure_time']
        arrival = train['arrival_time']
        text += (
            f"• KTX {train['train_no']} · {departure[:2]}:{departure[2:4]} → "
            f"{arrival[:2]}:{arrival[2:4]} · {seat} 예약 가능\n"
        )
    text += '\n성인 1명 기준입니다. 코레일에서 현재 좌석을 확인해 주세요.\nhttps://www.korail.com/ticket/search/list'
    try:
        response = requests.post(f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': chat_id, 'text': text, 'disable_web_page_preview': True}, timeout=10)
        response.raise_for_status()
        if response.json().get('ok') is not True:
            return False
        return True
    except Exception as exc:
        logging.getLogger(__name__).error('KTX Telegram delivery failed (%s)', type(exc).__name__)
        return False
