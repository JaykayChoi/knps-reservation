import requests

def send_telegram_notification(token, chat_id, reservations, is_test=False):
    if not token or not chat_id or not reservations:
        return

    header = "[TEST] 🔔" if is_test else "🔔"
    message = f"{header} *[국립공원 빈자리 알림]*\n\n"
    for res in reservations:
        date_str = f"{res['date'][:4]}-{res['date'][4:6]}-{res['date'][6:8]}"
        message += f"📅 *{date_str}*\n"
        message += f"📍 {res['park_name']} ({res['campsite_name']})\n"
        message += f"⛺ {res['facility_type']} - {res['available_count']}개\n"
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
        return True
    except Exception as e:
        print(f"Telegram error: {e}")
        return False
