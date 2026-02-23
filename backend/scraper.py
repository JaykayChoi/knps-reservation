import requests
import datetime

KNPS_API_URL = "https://reservation.knps.or.kr/reservation/selectCampRemainSiteList.do"

def get_target_dates(weeks, selected_days, specific_dates):
    today = datetime.date.today()
    target_dates = set()

    # Weekday based dates
    if weeks and selected_days:
        for i in range(weeks * 7):
            date = today + datetime.timedelta(days=i)
            # Python weekday(): Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
            if date.weekday() in selected_days:
                target_dates.add(date.strftime("%Y%m%d"))

    # Specific dates
    if specific_dates:
        for date_str in specific_dates:
            # specific_dates are expected in YYYY-MM-DD or YYYYMMDD
            clean_date = date_str.replace("-", "").replace(".", "")
            if len(clean_date) == 8:
                target_dates.add(clean_date)

    return sorted(list(target_dates))

def fetch_reservations(dates, facility_types, parks):
    results = []
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://reservation.knps.or.kr/reservation/searchCampRemainSite.do"
    }

    for date in dates:
        try:
            data = {"prd_sal_ymd": date, "park": ""}
            resp = requests.post(KNPS_API_URL, data=data, headers=headers, timeout=10)
            resp.raise_for_status()
            data_json = resp.json()

            for item in data_json.get("list", []):
                # Filter by facility type
                if facility_types and item.get("prdCtgNm") not in facility_types:
                    continue
                
                # Filter by park name
                if parks and item.get("officeNm") not in parks:
                    continue

                # Filter by availability
                if (item.get("cntN") or 0) > 0:
                    results.append({
                        "date": date,
                        "park_name": item.get("officeNm"),
                        "campsite_name": item.get("deptNm"),
                        "facility_type": item.get("prdCtgNm"),
                        "available_count": item.get("cntN"),
                        "identifier": f"{date}_{item.get('officeNm')}_{item.get('prdCtgNm')}"
                    })
        except Exception as e:
            print(f"Error fetching {date}: {e}")
            
    return results
