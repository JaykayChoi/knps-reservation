"""모두의주차장(app.modu.kr) 월정기권 재고 조회.

KNPS 스크래퍼와 마찬가지로 stateless 하게 동작하며, 인증/쿠키 없이
공개 JSON API(api.modu.cloud)를 사용한다. 지도 API가 대상 주차장을
반환하지 않는 경우에만 상세 페이지(SSR) 파싱으로 폴백한다.
"""

import json
import logging

import requests

logger = logging.getLogger(__name__)

MODU_PINS_URL = "https://api.modu.cloud/poi/pins"
MODU_DETAIL_URL = "https://app.modu.kr/map"

# 주차권 상품군. 시간권/당일권/심야권은 0, 월주차권 계열은 10000.
MONTHLY_COUPON_GROUP = 10000

# 감시 대상 주차장 (고정). geohash는 주차장 좌표에서 산출한 6자리 값으로,
# 두 곳 모두 같은 셀에 있어 지도 API 1회 호출로 커버된다.
PARKING_LOTS = [
    {"seq": 109902, "name": "투루파킹 KT&G타워 주차장", "geohash": "wydm77"},
    {"seq": 106112, "name": "카카오 T 대치사거리 주차장", "geohash": "wydm77"},
]


def get_parking_lots():
    """감시 가능한 주차장 목록 (프론트엔드 노출용)."""
    return [dict(lot) for lot in PARKING_LOTS]


def build_lot_url(seq):
    return f"{MODU_DETAIL_URL}?type=P&id={seq}#sheet=2"


def _fetch_pins(geohash):
    """geohash 셀의 주차장 핀 목록을 {parkinglotSeq: lot} 으로 반환."""
    try:
        resp = requests.get(
            MODU_PINS_URL,
            params={"geohash": geohash, "durationId": "PT1H"},
            timeout=10,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        logger.error(f"Modu pins fetch failed (geohash={geohash}): {e}")
        return {}

    lots = {}
    for entry in payload.get("data") or []:
        for lot in entry.get("parkinglots") or []:
            seq = lot.get("parkinglotSeq")
            if seq is not None:
                lots[seq] = lot
    return lots


def _extract_json_array(text, key):
    """RSC 페이로드에서 `"key":[ ... ]` 배열을 괄호 매칭으로 잘라 파싱."""
    marker = f'"{key}":'
    idx = text.find(marker)
    if idx == -1:
        return []
    start = text.find("[", idx)
    if start == -1:
        return []

    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except ValueError as e:
                    logger.error(f"Failed to parse '{key}' array: {e}")
                    return []
    return []


def _fetch_tickets_from_detail(seq):
    """상세 페이지 SSR 페이로드에서 주차권 목록을 파싱 (폴백 경로)."""
    try:
        resp = requests.get(
            MODU_DETAIL_URL,
            params={"type": "P", "id": seq},
            timeout=10,
        )
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        logger.error(f"Modu detail fetch failed (seq={seq}): {e}")
        return []

    # Next.js RSC 스트림: self.__next_f.push([1,"<escaped chunk>"])
    chunks = []
    marker = "self.__next_f.push([1,"
    pos = html.find(marker)
    while pos != -1:
        start = html.find('"', pos + len(marker))
        if start == -1:
            break
        i = start + 1
        escaped = False
        while i < len(html):
            ch = html[i]
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                break
            i += 1
        try:
            chunks.append(json.loads(html[start:i + 1]))
        except ValueError:
            pass
        pos = html.find(marker, i)

    return _extract_json_array("".join(chunks), "tickets")


def _normalize(lot, ticket):
    return {
        "lot_seq": lot["seq"],
        "lot_name": lot["name"],
        "ticket_name": ticket.get("couponName") or "월정기권",
        "coupon_seq": ticket.get("couponSeq"),
        "price": ticket.get("price") or 0,
        # 판매중 = 품절 아님 + 구매 오픈 상태
        "is_available": not ticket.get("isSoldOut", True) and bool(ticket.get("isOpen")),
        "url": build_lot_url(lot["seq"]),
    }


def fetch_monthly_passes(lot_seqs=None):
    """지정한 주차장들의 월정기권 상태를 조회한다.

    Args:
        lot_seqs: 조회할 주차장 seq 목록. None이면 전체 감시 대상.

    Returns:
        [{lot_seq, lot_name, ticket_name, coupon_seq, price, is_available, url}, ...]
    """
    if lot_seqs is None:
        lots = get_parking_lots()
    else:
        wanted = {str(s) for s in lot_seqs}
        lots = [lot for lot in get_parking_lots() if str(lot["seq"]) in wanted]

    if not lots:
        return []

    results = []
    pins_cache = {}
    for lot in lots:
        geohash = lot["geohash"]
        if geohash not in pins_cache:
            pins_cache[geohash] = _fetch_pins(geohash)

        pin = pins_cache[geohash].get(lot["seq"])
        if pin:
            tickets = pin.get("tickets") or []
        else:
            logger.warning(
                f"Lot {lot['seq']} not found in pins (geohash={geohash}); "
                "falling back to detail page"
            )
            tickets = _fetch_tickets_from_detail(lot["seq"])

        monthly = [t for t in tickets if t.get("couponTypeGroup") == MONTHLY_COUPON_GROUP]
        if not monthly:
            logger.info(f"No monthly pass listed for lot {lot['seq']} ({lot['name']})")
        for ticket in monthly:
            results.append(_normalize(lot, ticket))

    return results
