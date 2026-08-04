import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import modu_scraper
from notifier import send_parking_notification


def _pins_payload(seq, tickets):
    return {
        "data": [{"geohash": "wydm77", "parkinglots": [{"parkinglotSeq": seq, "tickets": tickets}]}],
        "tid": "1",
        "ts": 1,
    }


MONTHLY_SOLD_OUT = {
    "couponSeq": 22453, "couponName": "월정기권", "couponTypeGroup": 10000,
    "couponTypeSeq": 10200, "price": 242000, "isSoldOut": True, "isOpen": False,
}
MONTHLY_AVAILABLE = {
    "couponSeq": 22453, "couponName": "월정기권", "couponTypeGroup": 10000,
    "couponTypeSeq": 10200, "price": 242000, "isSoldOut": False, "isOpen": True,
}
HOURLY_TICKET = {
    "couponSeq": 26831, "couponName": "평일 1시간권", "couponTypeGroup": 0,
    "couponTypeSeq": 2000, "price": 3800, "isSoldOut": False, "isOpen": True,
}


def _mock_get(payload):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    return resp


def test_get_parking_lots_returns_two_fixed_lots():
    lots = modu_scraper.get_parking_lots()
    assert [lot["seq"] for lot in lots] == [109902, 106112]
    # 방어적 복사본이어야 원본 상수가 오염되지 않는다
    lots[0]["seq"] = 0
    assert modu_scraper.get_parking_lots()[0]["seq"] == 109902


@patch('modu_scraper.requests.get')
def test_fetch_monthly_passes_detects_sold_out(mock_get):
    mock_get.return_value = _mock_get(_pins_payload(109902, [HOURLY_TICKET, MONTHLY_SOLD_OUT]))

    result = modu_scraper.fetch_monthly_passes([109902])

    assert len(result) == 1
    assert result[0]["lot_seq"] == 109902
    assert result[0]["lot_name"] == "투루파킹 KT&G타워 주차장"
    assert result[0]["ticket_name"] == "월정기권"
    assert result[0]["price"] == 242000
    assert result[0]["is_available"] is False


@patch('modu_scraper.requests.get')
def test_fetch_monthly_passes_detects_available(mock_get):
    mock_get.return_value = _mock_get(_pins_payload(109902, [MONTHLY_AVAILABLE]))

    result = modu_scraper.fetch_monthly_passes([109902])

    assert len(result) == 1
    assert result[0]["is_available"] is True
    assert result[0]["url"] == "https://app.modu.kr/map?type=P&id=109902#sheet=2"


@patch('modu_scraper.requests.get')
def test_fetch_monthly_passes_ignores_non_monthly_tickets(mock_get):
    mock_get.return_value = _mock_get(_pins_payload(109902, [HOURLY_TICKET]))

    assert modu_scraper.fetch_monthly_passes([109902]) == []


@patch('modu_scraper.requests.get')
def test_fetch_monthly_passes_shares_single_call_per_geohash(mock_get):
    """두 주차장이 같은 geohash 셀이므로 지도 API는 1번만 호출돼야 한다."""
    mock_get.return_value = _mock_get({
        "data": [{"geohash": "wydm77", "parkinglots": [
            {"parkinglotSeq": 109902, "tickets": [MONTHLY_SOLD_OUT]},
            {"parkinglotSeq": 106112, "tickets": [dict(MONTHLY_AVAILABLE, couponSeq=27089, price=143000)]},
        ]}]
    })

    result = modu_scraper.fetch_monthly_passes([109902, 106112])

    assert mock_get.call_count == 1
    assert len(result) == 2
    assert result[1]["lot_seq"] == 106112
    assert result[1]["price"] == 143000
    assert result[1]["is_available"] is True


@patch('modu_scraper.requests.get')
def test_fetch_monthly_passes_filters_unknown_seq(mock_get):
    assert modu_scraper.fetch_monthly_passes([999999]) == []
    mock_get.assert_not_called()


@patch('modu_scraper.requests.get')
def test_fetch_monthly_passes_survives_network_error(mock_get):
    mock_get.side_effect = Exception("boom")
    # 핀 조회 실패 -> 상세 페이지 폴백도 실패 -> 빈 결과, 예외 전파 없음
    assert modu_scraper.fetch_monthly_passes([109902]) == []


@patch('modu_scraper.requests.get')
def test_falls_back_to_detail_page_when_lot_missing_from_pins(mock_get):
    detail_tickets = [HOURLY_TICKET, MONTHLY_AVAILABLE]
    flight = json.dumps({"tickets": detail_tickets}, ensure_ascii=False)
    html = f'<script>self.__next_f.push([1,{json.dumps(flight)}])</script>'

    pins_resp = _mock_get({"data": [{"geohash": "wydm77", "parkinglots": []}]})
    detail_resp = MagicMock()
    detail_resp.raise_for_status.return_value = None
    detail_resp.text = html
    mock_get.side_effect = [pins_resp, detail_resp]

    result = modu_scraper.fetch_monthly_passes([109902])

    assert mock_get.call_count == 2
    assert len(result) == 1
    assert result[0]["is_available"] is True


def test_extract_json_array_handles_nested_brackets_and_strings():
    text = '{"tickets":[{"name":"a]b","tags":[1,2]},{"name":"c"}],"other":1}'
    assert modu_scraper._extract_json_array(text, "tickets") == [
        {"name": "a]b", "tags": [1, 2]}, {"name": "c"}
    ]


def test_extract_json_array_returns_empty_when_key_absent():
    assert modu_scraper._extract_json_array('{"foo":1}', "tickets") == []


@patch('requests.post')
def test_send_parking_notification_message(mock_post):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    mock_post.return_value = resp

    passes = [{
        "lot_seq": 109902,
        "lot_name": "투루파킹 KT&G타워 주차장",
        "ticket_name": "월정기권",
        "price": 242000,
        "is_available": True,
        "url": "https://app.modu.kr/map?type=P&id=109902#sheet=2",
    }]

    assert send_parking_notification("t", "c", passes, is_test=True) is True
    message = mock_post.call_args.kwargs['json']['text']
    assert "[TEST]" in message
    assert "투루파킹 KT&G타워 주차장" in message
    assert "242,000원" in message
    assert "id=109902" in message


@patch('requests.post')
def test_send_parking_notification_skips_empty(mock_post):
    assert send_parking_notification("t", "c", [], is_test=False) is False
    mock_post.assert_not_called()


@patch('requests.post')
def test_send_parking_notification_returns_false_on_error(mock_post):
    mock_post.side_effect = Exception("telegram down")
    passes = [{"lot_seq": 1, "lot_name": "L", "ticket_name": "월정기권", "price": 100, "url": "u"}]
    assert send_parking_notification("t", "c", passes) is False
