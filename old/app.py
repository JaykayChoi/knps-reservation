from flask import Flask, render_template, jsonify, request
import requests
import datetime
import os

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

def _parse_date(s: str):
    """YYYY-MM-DD 또는 YYYY.MM.DD 허용. 잘못되면 None."""
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y.%m.%d"):
        try:
            return datetime.datetime.strptime(s.strip(), fmt).date()
        except Exception:
            pass
    return None

@app.route("/api/reservations")
def reservations():
    today = datetime.date.today()

    # ✅ 주수 파라미터 (1~10), 기본 8주
    try:
        weeks = int(request.args.get("weeks", "8"))
    except Exception:
        weeks = 8
    if weeks < 1 or weeks > 10:
        weeks = 8
    total_days = weeks * 7

    # ✅ 요일 파라미터: Python weekday() 기준 (월=0 ... 일=6). 기본값: 토요일(5)
    raw_days = request.args.get("days", "5")
    try:
        selected_days = {int(x) for x in raw_days.split(",") if x != ""}
        selected_days = {d for d in selected_days if 0 <= d <= 6}
    except Exception:
        selected_days = {5}
    if not selected_days:
        selected_days = {5}

    # ✅ 시설 파라미터: 기본값 세 가지(특화야영장, 카라반, 자동차야영장)
    raw_types = request.args.get("types", "특화야영장,카라반,자동차야영장")
    selected_types = {x.strip() for x in raw_types.split(",") if x.strip()}
    if not selected_types:
        selected_types = {"특화야영장", "카라반", "자동차야영장"}

    # ✅ 날짜 범위 파라미터 (있으면 ‘추가로’ 포함; 요일/주수와 합집합)
    start_str = (request.args.get("start_date") or "").strip()
    end_str   = (request.args.get("end_date") or "").strip()
    start_date = _parse_date(start_str)
    end_date   = _parse_date(end_str)

    # ✅ 요일 기반 후보 (오늘부터 weeks*7일 중 선택 요일만)
    weekday_dates = [
        (today + datetime.timedelta(days=i)).strftime("%Y%m%d")
        for i in range(total_days)
        if (today + datetime.timedelta(days=i)).weekday() in selected_days
    ]

    # ✅ 날짜 범위 후보 (양 끝 포함, 과도 방지를 위해 최대 120일)
    range_dates = []
    if start_date and end_date and start_date <= end_date:
        max_span = 120
        span = (end_date - start_date).days + 1
        if span > max_span:
            end_date = start_date + datetime.timedelta(days=max_span - 1)
            span = max_span
        range_dates = [
            (start_date + datetime.timedelta(days=i)).strftime("%Y%m%d")
            for i in range(span)
        ]

    # ✅ 최종 타깃: 합집합(중복 제거)
    target_dates = sorted(set(weekday_dates) | set(range_dates))

    print(
        f"[API] 주수={weeks}, 요일={sorted(selected_days)}, 시설={sorted(selected_types)} "
        f"/ 날짜범위={start_date}~{end_date} / (요일 {len(weekday_dates)} + 범위 {len(range_dates)}) "
        f"→ 조회일자수={len(target_dates)}"
    )

    filtered_results = []
    for date in target_dates:
        try:
            url = "https://reservation.knps.or.kr/reservation/selectCampRemainSiteList.do"
            data = {"prd_sal_ymd": date, "park": ""}
            headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest"
            }
            resp = requests.post(url, data=data, headers=headers, timeout=10)
            resp.raise_for_status()
            result = resp.json()

            filtered = [
                {**item, "query_date": date}
                for item in result.get("list", [])
                if item.get("prdCtgNm") in selected_types
                and (item.get("cntN") or 0) > 0
            ]
            filtered_results.extend(filtered)

        except Exception as e:
            print(f"[{date}] 호출 실패: {e}")

    return jsonify(filtered_results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[INFO] Starting server on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
