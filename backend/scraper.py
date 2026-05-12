import os
import datetime
import logging
import requests

logger = logging.getLogger(__name__)

KNPS_BASE = "https://reservation.knps.or.kr"
KNPS_LOGIN_PAGE = f"{KNPS_BASE}/mmb/mmbLogin.do"
KNPS_LOGIN_URL = f"{KNPS_BASE}/mmb/mmbLoginProc.do"
KNPS_REMAIN_PAGE = f"{KNPS_BASE}/reservation/searchCampRemainSite.do"
KNPS_API_URL = f"{KNPS_BASE}/reservation/selectCampRemainSiteList.do"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def get_target_dates(weeks, selected_days, specific_dates, date_mode="weekday"):
    today = datetime.date.today()
    target_dates = set()
    if date_mode == "weekday":
        if weeks and selected_days:
            for i in range(weeks * 7):
                date = today + datetime.timedelta(days=i)
                if date.weekday() in selected_days:
                    target_dates.add(date.strftime("%Y%m%d"))
    elif date_mode == "absolute":
        if specific_dates:
            for date_str in specific_dates:
                clean_date = date_str.replace("-", "").replace(".", "")
                if len(clean_date) == 8:
                    target_dates.add(clean_date)
    return target_dates


def _build_session():
    """Create a requests.Session and authenticate against KNPS.

    Returns the logged-in session, or None if credentials missing / login failed.
    """
    username = os.environ.get("KNPS_USERNAME")
    password = os.environ.get("KNPS_PASSWORD")
    if not username or not password:
        logger.error("KNPS_USERNAME / KNPS_PASSWORD env vars are not set")
        return None

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # Prime JSESSIONID
    try:
        session.get(KNPS_LOGIN_PAGE, timeout=10)
    except Exception as e:
        logger.error(f"KNPS login page fetch failed: {e}")
        return None

    try:
        resp = session.post(
            KNPS_LOGIN_URL,
            data={"loginType": "Member", "mmbId": username, "passWd": password},
            headers={"Referer": KNPS_LOGIN_PAGE},
            timeout=10,
            allow_redirects=True,
        )
    except Exception as e:
        logger.error(f"KNPS login request failed: {e}")
        return None

    # Successful login redirects away from mmbLogin; failure typically lands back on it.
    final_url = resp.url or ""
    if "mmbLogin" in final_url or "loginFail" in resp.text or "비밀번호" in resp.text and "일치" in resp.text:
        logger.error(f"KNPS login appears to have failed (final_url={final_url}, status={resp.status_code})")
        return None

    # Warm up the remain-site page so subsequent AJAX gets proper Referer context.
    try:
        session.get(KNPS_REMAIN_PAGE, timeout=10)
    except Exception:
        pass

    logger.info("KNPS login successful")
    return session


def fetch_reservations(dates, facility_types, parks):
    results = []
    if not dates:
        return results

    session = _build_session()
    if session is None:
        return results

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": KNPS_REMAIN_PAGE,
        "Origin": KNPS_BASE,
    }

    null_count = 0
    for date in dates:
        try:
            resp = session.post(
                KNPS_API_URL,
                data={"prd_sal_ymd": date, "park": ""},
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            data_json = resp.json()

            raw_list = data_json.get("list")
            if raw_list is None:
                null_count += 1

            for item in (raw_list or []):
                if facility_types and item.get("prdCtgNm") not in facility_types:
                    continue
                if parks and item.get("officeNm") not in parks:
                    continue

                cnt_n = item.get("cntN") or 0
                cnt_w = item.get("cntW") or 0
                if cnt_n > 0 or cnt_w > 0:
                    results.append({
                        "date": date,
                        "park_name": item.get("officeNm"),
                        "campsite_name": item.get("deptNm"),
                        "facility_type": item.get("prdCtgNm"),
                        "available_count": cnt_n,
                        "waiting_count": cnt_w,
                    })
        except Exception as e:
            logger.error(f"Error fetching {date}: {e}")

    if null_count and null_count == len(dates):
        logger.warning(
            f"KNPS API returned null list for ALL {null_count} dates — "
            "session may not be authenticated. Check KNPS_USERNAME/KNPS_PASSWORD."
        )

    return results
