import logging
from unittest.mock import Mock

import pytest
import requests

from providers import ktx

OPTIONS = {
    'departure': '서울', 'arrival': '부산', 'date': '2099-10-01',
    'start_time': '08:00', 'end_time': '18:00',
    'seat_classes': ['general', 'special', 'standing'],
}


def raw(no='001', time='090000', general='13', special='13', standing='00'):
    return {
        'h_trn_no': no, 'h_dpt_dt': '20991001', 'h_dpt_tm': time,
        'h_arv_tm': '120000', 'h_dpt_rs_stn_nm': '서울',
        'h_arv_rs_stn_nm': '부산', 'h_gen_rsv_cd': general,
        'h_spe_rsv_cd': special, 'h_stnd_rsv_cd': standing,
    }


class Client:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []
        self.closed = False

    def search_page(self, *args):
        self.calls.append(args)
        return self.pages.pop(0) if self.pages else []

    def close(self):
        self.closed = True


def test_anonymous_results_paginate_and_map_all_selected_classes():
    client = Client([[raw(general='11')], [raw('002', '100000', special='11', standing='11')], []])
    rows = ktx.fetch_availability(OPTIONS, client=client)
    assert [(row['train_no'], row['seat_class']) for row in rows] == [
        ('001', 'general'), ('002', 'special'), ('002', 'standing')]
    assert client.calls[1][-1] == '090001'


def test_unselected_classes_and_out_of_window_are_ignored():
    client = Client([[raw(time='075900', general='11'), raw('002', '090000', special='11')], []])
    rows = ktx.fetch_availability({**OPTIONS, 'seat_classes': ['general']}, client=client)
    assert rows == []


def test_past_date_skips_client_creation(mocker):
    create = mocker.patch('providers.ktx.OfficialKorailClient')
    assert ktx.fetch_availability({**OPTIONS, 'date': '2000-01-01'}) == []
    create.assert_not_called()


def test_direct_client_posts_official_anonymous_contract_and_handles_results():
    response = Mock()
    response.json.return_value = {'strResult': 'SUCC', 'trn_infos': {'trn_info': [raw()]}}
    session = Mock(); session.post.return_value = response
    signer = Mock(); signer.token.return_value = 'signed'
    client = ktx.OfficialKorailClient(session=session, signer=signer)
    assert client.search_page('서울', '부산', '20991001', '080000') == [raw()]
    call = session.post.call_args
    assert call.args[0] == ktx.SCHEDULE_URL
    assert call.kwargs['params']['txtPsgFlg_1'] == '1'
    assert call.kwargs['params']['txtTrnGpCd'] == '100'
    assert call.kwargs['headers']['x-dynapath-m-token'] == 'signed'
    assert call.kwargs['timeout'] == (5, 15)


def test_direct_client_distinguishes_empty_from_upstream_error():
    response = Mock(); session = Mock(); session.post.return_value = response
    response.json.return_value = {'strResult': 'FAIL', 'h_msg_cd': 'P100'}
    assert ktx.OfficialKorailClient(session=session).search_page('서울', '부산', '20991001', '080000') == []
    response.json.return_value = {'strResult': 'FAIL', 'h_msg_cd': 'MACRO ERROR'}
    with pytest.raises(ktx.KtxError, match='rejected'):
        ktx.OfficialKorailClient(session=session).search_page('서울', '부산', '20991001', '080000')


def test_signer_matches_fixed_official_request_vector():
    signer = ktx.DynaPathSigner(started_at=1700000000000)
    token = signer.token(timestamp=1700000001234, nonce='AB12')
    assert token == ('bEeEPSYj1Dm5CMM4Pv4ff4GR4GR4GR4GDK3FFmJaRyn3PkmGmvPkqJaRPyD3wdPv1f5G4wMCMfmudCEaGPGGPmGldCMG41Gf513Pff3myw5mug4CRCn9JlJC1vJdD4nnJEv4uYmRfGkgJE9JgqCMKJl44uGCMYf5d3kg4mPPvv4uCJkg4al4mPPvv4uC4133kg4mPPvv4uC4YYyndJa133Mf5v3lJGllGPfGPfGPfGPfGPfG4j3jymknCjdGPfGPfGPfGlPC1vf5F3lJG4jPkMmknCDk4nCynDvlFa5mCnfvkj3YKmkMPd33qq4jwf5dY1CYD5')


def test_http_failure_logs_only_status_and_host(caplog):
    response = requests.Response()
    response.status_code = 403
    response.url = ktx.SCHEDULE_URL + '?secret=must-not-appear'
    client = Mock()
    client.search_page.side_effect = requests.HTTPError(response=response)

    with caplog.at_level(logging.ERROR), pytest.raises(ktx.KtxError):
        ktx.fetch_availability(OPTIONS, client=client)

    assert 'HTTP 403 from smart.letskorail.com' in caplog.text
    assert 'secret' not in caplog.text


def test_station_list_is_normalized_and_session_timeout_is_explicit():
    session = Mock()
    session.get.return_value.json.return_value = {'stns': {'stn': [
        {'stn_cd': '0001', 'stn_nm': '서울', 'area': '0', 'major': '1'},
        {'stn_cd': '0020', 'stn_nm': '부산', 'area': '9'},
    ]}}
    assert ktx.fetch_stations(session=session) == [
        {'code': '0001', 'name': '서울', 'area': '0', 'major': 1},
        {'code': '0020', 'name': '부산', 'area': '9', 'major': None},
    ]
    session.get.assert_called_once_with(ktx.STATIONS_URL, timeout=(5, 15))
