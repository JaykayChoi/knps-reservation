import os
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


class KnpsError(RuntimeError):
    pass


def _build_session():
    """Create a requests.Session and authenticate against KNPS.

    Returns a logged-in session.
    """
    username = os.environ.get("KNPS_USERNAME")
    password = os.environ.get("KNPS_PASSWORD")
    if not username or not password:
        raise KnpsError("KNPS credentials are not configured")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # Prime JSESSIONID
    try:
        session.get(KNPS_LOGIN_PAGE, timeout=10)
    except Exception:
        session.close()
        raise KnpsError("KNPS login page request failed") from None

    try:
        resp = session.post(
            KNPS_LOGIN_URL,
            data={"loginType": "Member", "mmbId": username, "passWd": password},
            headers={"Referer": KNPS_LOGIN_PAGE},
            timeout=10,
            allow_redirects=True,
        )
    except Exception:
        session.close()
        raise KnpsError("KNPS login request failed") from None

    # Successful login redirects away from mmbLogin; failure typically lands back on it.
    final_url = resp.url or ""
    if "mmbLogin" in final_url or "loginFail" in resp.text or "비밀번호" in resp.text and "일치" in resp.text:
        session.close()
        raise KnpsError("KNPS login was rejected")

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

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": KNPS_REMAIN_PAGE,
        "Origin": KNPS_BASE,
    }

    null_count = 0
    errors = []
    try:
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
            except Exception as exc:
                logger.error("KNPS availability failed for %s (%s)", date, type(exc).__name__)
                errors.append(date)
    finally:
        session.close()

    if null_count and null_count == len(dates):
        logger.warning(
            f"KNPS API returned null list for ALL {null_count} dates — "
            "session may not be authenticated. Check KNPS_USERNAME/KNPS_PASSWORD."
        )

    if errors:
        raise KnpsError(f"KNPS availability failed for {len(errors)} date(s)")
    if null_count and null_count == len(dates):
        raise KnpsError("KNPS returned no data for every requested date")
    return results
