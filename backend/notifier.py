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