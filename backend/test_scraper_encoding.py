import requests

KNPS_API_URL = "https://reservation.knps.or.kr/reservation/selectCampRemainSiteList.do"
headers = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://reservation.knps.or.kr/reservation/searchCampRemainSite.do"
}

date = '20260228'
data = {"prd_sal_ymd": date, "park": ""}

try:
    resp = requests.post(KNPS_API_URL, data=data, headers=headers, timeout=10)
    resp.raise_for_status()
    
    print('Content-Type:', resp.headers.get('Content-Type'))
    print('Raw bytes sample:', resp.content[:100])
    print('Text sample:', resp.text[:100])
    
    # Try to decode as EUC-KR
    try:
        euc_text = resp.content.decode('euc-kr')
        print('EUC-KR decode text sample:', euc_text[:100])
        import json
        data_json = json.loads(euc_text)
        print('EUC-KR JSON success')
        print('First item:', data_json.get("list", [])[0] if data_json.get("list") else 'No list')
    except Exception as e_euc:
        print(f'EUC-KR decode failed: {e_euc}')
            
except Exception as e:
    print(f'Request failed: {e}')
