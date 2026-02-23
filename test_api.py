import requests
import json

url = "http://127.0.0.1:5000/api/settings"
payload = {
    "weeks_ahead": 4,
    "start_date": "2026-03-01",
    "end_date": "2026-03-10",
    "cooldown_days": 1,
    "telegram_bot_token": "TEST_TOKEN",
    "telegram_chat_id": "TEST_ID",
    "selected_days": ["Fri", "Sat"],
    "selected_types": ["특화야영장"],
    "selected_parks": ["지리산"]
}

print(f"Testing POST {url} with payload: {payload}")
try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
