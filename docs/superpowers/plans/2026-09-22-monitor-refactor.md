# 모니터링 시스템 전체 리팩토링 구현 계획

> **인계받는 모델:** 현재는 계획 검토 단계다. 사용자의 명시적 구현 승인 전 실행하지 않는다. 승인 후 이 문서와 설계를 먼저 읽고, `superpowers:executing-plans` 방식으로 단계별 구현·검증한다. 사용자/저장소 지침에 없는 subagent 위임이나 Git 작업을 시작하지 않는다.

**Goal:** 설정별 알림 중지 시간과 카테고리별 공통 JSON 스키마를 도입하면서 전체 활성 코드의 책임·명명·오류 처리·테스트를 정리한다.

**Architecture:** 공통 Monitor/options → category provider → 공통 availability/notification pipeline → Supabase history. Flask 라우트와 바닐라 JS는 경계만 담당한다. 카테고리 차이는 검증기·provider·formatter에 모은다.

**Tech Stack:** Python 3.13+, Flask, Requests, Supabase/PostgreSQL 17, vanilla JS ES modules, Tailwind, pytest, Playwright. 현재 로컬 Python은 3.14.3으로 확인된 기록이 있으므로 실제 실행 버전도 보고한다.

**Spec:** [전체 설계](../specs/2026-09-22-monitor-refactor-design.md)

## 승인·실행 규칙

- 현재 산출물은 이 계획과 설계뿐이다. 코드·마이그레이션·테스트 구현은 아직 없다.
- 이 계획에 대한 사용자 승인 후에만 Task 0을 시작한다.
- 작업은 현재 master에서 수행한다. AGENTS.md에 따라 명시적 요청 없는 commit/push/branch/PR 금지.
- 로컬 완료 후 운영 배포/마이그레이션을 사용자에게 다시 묻고 멈춘다. 기존 세션의 배포 허가는 이번 변경에 재사용하지 않는다.
- `.env*`, `config.ini`의 운영 자격 증명을 테스트에 사용하지 않는다. 모든 테스트 프로세스는 env를 명시적으로 격리한다.
- `old/`, 적용된 migrations, `.claude/`는 그대로 둔다. 자료 중 코드와 모순되는 과거 README/QA는 코드보다 우선하지 않는다.
- 테스트는 구현을 흉내 내는 assertion 대신 동작과 실패 경계를 검증한다. 기존 잘못된 동작을 고칠 때는 설계의 변경 목록을 근거로 테스트 기대치를 바꾼다.

## 우선 리뷰할 다섯 가지 위험

1. 조회 시작 후 수면 시간에 들어가거나 설정이 삭제되는 경우: 전송 직전 최신 정책 검사로 차단되어야 한다.
2. 마이그레이션이 KTX 구형 scalar, 새 array, KNPS 빈 요일/추가 날짜 범위, 비활성 행을 다른 의미로 바꾸면 안 된다.
3. 같은 채널의 두 설정 및 다중 batch 일부 실패: 다른 설정을 중지하거나 미발송 항목을 이력에 쓰면 안 된다.
4. rename/drop 이후 구버전 프로세스가 살아 있으면 서비스가 깨진다. 점검 시간의 drain·차단·배포·롤백 순서를 반드시 리허설한다.
5. 외부 서비스 오류·DB 오류를 '빈 결과/성공'으로 오인하거나 테스트가 운영 서비스에 연결되면 안 된다.

## 작업 의존 관계

```text
0 안전한 기준선
  └─1 공통 모델·정책
      ├─2 SQL 이전·역변환
      │   └─3 저장소
      ├─4 providers
      └─5 메시지·transport
          └─6 공통 실행·알림 서비스 (3,4,5 필요)
              └─7 API·앱 구성
                  └─8 프런트엔드·검색
                      └─9 문서·죽은 코드 정리
                          └─10 전체 로컬 검증·리뷰
                              └─STOP: 운영 승인 질문
```

각 task는 먼저 실패 테스트 → 기대한 실패 확인 → 구현 → 해당 테스트 통과 순서로 진행한다. 광범위한 전체 테스트를 매 편집마다 반복하지 않고 주요 통합 지점에서 실행한다. 진행표를 갱신하되 지나간 실패를 통과로 숨기지 않는다.

## Task 0. 기준선과 안전한 테스트 환경

**파일:** `AGENTS.md` 확인; `pyproject.toml` 또는 `pytest.ini`, `backend/tests/conftest.py`, `playwright.config.ts`, `tests/fixtures/`; 수동 스크립트 3개.

- [ ] `git status --short`, 현재 HEAD, 실제 파일 구조를 재확인한다. 사용자 변경이 있으면 보존하며 계획과 충돌 여부를 보고한다.
- [ ] `app.py`, `db.py`, providers, settings_model, notifier, 두 HTML, 테스트와 SQL을 재확인한다. 이번 설계는 c2aaefc 기준이므로 이후 변경을 덮어쓰지 않는다.
- [ ] 안전한 기존 backend suite와 네트워크가 완전히 mock된 `tests/categories.spec.ts`를 실행하여 기준선을 기록한다. 이전 115개 통과 기록을 새 실행으로 대체한다.
- [ ] unit 기본 세션에서 실제 Requests/socket/ Supabase 접속을 막는 fixture를 만든다. 외부 요청이 필요한 테스트는 별도 marker + 명시적 local/opt-in 환경에서만 허용한다. 테스트 순서가 달라도 전역 `_supabase`가 새지 않게 한다.
- [ ] `test_api.py`, `backend/test_scraper_encoding.py`, `backend/test_scraper_standalone.py`는 읽기만 한 뒤 `scripts/manual/`로 이동·명명하고 main guard와 명시적 URL/날짜 입력을 추가한다. 기본 pytest 수집에서 제외한다. 실제 실행하지 않는다.
- [ ] Playwright 기본 project는 intercepted fixture 기반으로 제한한다. 실제 Flask/DB 테스트는 `local-integration` project와 localhost URL 확인을 필수로 한다. 사용자의 기존 localhost:5000 서버를 자동 테스트 대상으로 삼지 않는다.
- [ ] Docker 연결만 확인하고 이번 task용 컨테이너/포트를 정한다. 기존 container/volume 삭제 금지.

**통과 조건:** 외부 HTTP를 시도하는 테스트는 명확히 실패하며 baseline 테스트가 fake 의존성으로 통과한다. 운영 설정 파일이 fixture에서 로드되지 않는다.

## Task 1. 공통 모델·options 검증·시간 정책

**생성:** `backend/domain/{models,settings,clock,schedules,notification_policy}.py`, `backend/api/legacy_settings.py`, 해당 테스트.

**인터페이스:** 설계의 Monitor/MonitorInput, HistoryKey, Availability, QueryResult, DeliveryBatch. datetime은 aware 값만 허용한다.

- [ ] normalize_monitor 계약 테스트: 3 category options, unknown fields, nested null/type, bool numeric, bounds, dates, station code pair, seat_classes dedup.
- [ ] 부분 업데이트 테스트: name/is_active/quiet-only 변경이 옵션을 보존, options 제공은 전체 교체, category 전환 시 새 options 필수, 원본 dict 비변경.
- [ ] legacy adapter 테스트: selected_* → options, legacy KTX classes mapping, canonical+legacy 충돌 거절, field whitelist. core 모델은 legacy field를 받지 않는다.
- [ ] quiet-hours table-driven 테스트: OFF, 22:59/23:00/06:59/07:00, 낮 구간, UTC 입력, 동일 시간 오류, HH:MM 이외 입력, disabled 값 복원.
- [ ] 날짜 정책 테스트: KST 자정과 UTC 전날, 윤년, Mon~Sun, weekday+range union, 중복 제거, 120일 경계, weeks=0, 역전/불가능 날짜.
- [ ] 순수 함수와 dataclass/TypedDict 중 책임에 맞는 최소 구조를 구현한다. 과도한 상속·validation 라이브러리 도입 금지.
- [ ] defaults를 한 곳에서 정의하고 GUI/API 신규 생성의 불일치를 제거한다. 기존 설정은 migration semantic mapping으로 보존한다.

**통과 조건:** DB/HTTP import 없이 모든 모델/시간 테스트 실행 가능. KST 기준과 options update 의미가 문서·테스트에서 동일.

## Task 2. DB 스키마 정규화와 로컬 migration 검증

**생성:**

- `supabase/migrations/<new-14-digit-version>_generalize_monitors.sql`
- `scripts/db/monitor_refactor_preflight.sql`
- `scripts/db/monitor_refactor_verify.sql`
- `scripts/db/monitor_refactor_rollback.sql`
- `tests/database/legacy_baseline.sql`, `refactor_fixture.sql`, `refactor_assertions.sql`
- `scripts/test-local-migration.ps1`

**신규 최종 스키마:** 설계 4절의 monitor_settings, options, quiet columns, 범용 history key names, catalog, atomic maintenance metadata.

- [ ] 실제 운영 DB 대신 disposable PostgreSQL 17에서 실행할 명시적 legacy baseline 작성. 과거 migration 파일명 중복을 숨기려 파일을 고치거나 연결된 DB reset 하지 않는다. baseline의 출처/현재 지원 버전 명시.
- [ ] fake rows: KNPS weekday/absolute/empty days/integer days/추가 기간, Parking 여러 lot, KTX legacy 3종+배열/standing/코드 없는 행, inactive, cooldown 0/30, Korean labels, timestamp, history를 준비한다.
- [ ] forward 적용 전후 row IDs/counts, category별 options 의미, timestamps/credentials의 동일성은 SQL boolean으로 비교하고 실제 비밀값을 로그에 출력하지 않는다.
- [ ] 테이블 rename, options backfill, quiet OFF 초기화, constraints 교체, legacy columns drop, identity sequence 교정, history FK BIGINT/rename/index 수행.
- [ ] jsonb 검증 함수/제약에 missing key, null, scalar/array 혼동, unknown category fields, invalid enum, empty seats 케이스를 넣는다. NULL check 우회가 없어야 한다.
- [ ] 신규 catalog에 기존 공원/시설/주차장 목록을 데이터로 이전한다. PARKING_LOTS 하드코딩을 새 provider로 옮기지 않는다. 실제 선택은 options에 보존한다.
- [ ] 모니터 create RPC: transaction lock 아래 최대 10개 제한, identity ID 생성, validation 적용. 동시 두 연결 create 테스트에서 중복 ID/11번째 행이 없어야 한다.
- [ ] 자정 maintenance RPC: KST 첫 분 한정, 같은 날짜 한 번, transaction으로 초기화 날짜 기록. 두 연결 동시 실행 검증.
- [ ] 기존 grants/RLS 정책·FK·인덱스·함수 참조 보존 테스트. SECURITY DEFINER가 필요하면 search_path 고정과 최소 execute 권한.
- [ ] rollback SQL 작성: 신규 데이터 파괴 없이 기존 모양 복원 가능한 배포 전 쓰기 차단 창을 기준으로 테스트. 새 quiet policy는 별도 보호 backup 대상. schema+migration ledger 복원 순서 명시.
- [ ] forward → assertions → rollback → legacy assertions → forward를 실행한다. 의도적으로 잘못된 행을 넣어 forward 전체가 rollback되는지도 검증.
- [ ] 새 migration은 한 번만 적용되는 것으로 운영 도구가 version을 확인; 이미 적용됐다는 이유로 잘못된 부분 상태를 IF NOT EXISTS로 덮어씌우지 않는다.

**통과 조건:** fake 기존 데이터와 이력 보존, 새 제약, 동시성, 역변환 모두 로컬에서 검증. 원격 migration 호출 없음.

## Task 3. 저장소와 앱 설정의 책임 분리

**생성:** `backend/config.py`, `backend/repositories/{client,monitors,history,catalogs,status}.py`.
**대체:** `backend/db.py` (전환 완료 후 삭제; 영구 re-export 껍데기 유지하지 않음).

- [ ] repository 계약 테스트를 작성한다. fake client와 실제 로컬 PostgREST 테스트를 분리하고 깊은 mock 체인 위주 테스트를 간단한 fake로 대체한다.
- [ ] dotenv는 앱 생성 시 명시적으로만 로드. `create_app(test_config, dependencies)`에서 client factory/clock/HTTP를 주입한다. import 자체가 DB 연결이나 worker 시작을 하지 않게 한다.
- [ ] CRUD가 canonical monitor_settings/options만 읽고 쓰도록 구현. delete SQL은 route가 아니라 repository에서 수행한다.
- [ ] count/max(id)+1 로직 제거, create RPC 사용. not found/validation/db unavailable 예외 타입 구분.
- [ ] cooldown 계산을 UTC로 통일, 0이면 DB 접근 없음, 성공 batch 기록 한 번으로 모으기. 이력 조회 실패를 cooldown 없음으로 간주하지 않는다.
- [ ] status 갱신은 upsert 또는 명확한 DB 함수로 정리. history 유지보수 실패와 조회 결과를 구별하고 오류 로그에서 비밀 제거.
- [ ] 레거시 컬럼 부재 fallback과 no-client silent-success 삭제. 테스트용 의존성은 explicit fake만 허용.

**통과 조건:** CRUD/options round-trip이 로컬 PostgREST까지 통과. fake 환경과 실제 앱 초기화가 서로 오염되지 않음.

## Task 4. 카테고리 providers와 조회 캐시

**이동/정리:** `scraper.py`→`providers/knps.py`, `modu_scraper.py`→`providers/moduparking.py`, `ktx_scraper.py`→`providers/ktx.py`, `providers/registry.py`.

- [ ] 각 provider의 외부 payload fixture를 만들고 공통 Availability에 대한 테스트부터 작성. old/raw 데이터 필드는 provider 내부에만 남긴다.
- [ ] KNPS 로그인 실패, 모든 날짜 null, 일부 날짜 실패, EUC-KR/UTF-8, 세션 close, 날짜/시설/공원 필터를 구분한다. 기존 유효 응답을 바꾸지 않는다.
- [ ] Modu pins 1회/geohash, missing lot→SSR fallback, malformed RSC, fallback 최종 실패, 정상 tickets=[]를 구별한다. 입력 catalog entries와 selected IDs를 명시적으로 전달한다.
- [ ] KTX `auto_login=False`, isolated timeout session, sold-out pagination, 시간 양 끝, 다음 날 방지, page ceiling, 원본 h_stnd_rsv_cd=11과 waitlist 분리 테스트.
- [ ] `TimeoutSession` 실제 mocked Response JSON을 통과시키는 테스트를 추가해 standing map 생성과 train lookup 연결을 확인한다. map을 직접 넣는 테스트만으로 검증을 끝내지 않는다.
- [ ] seat_classes 배열이 포함된 options로 여러 monitor를 실행하는 캐시 회귀 테스트 작성. 동일 조건 한 번 조회, 다른 조건 분리, 순서 무관 집합 canonical key 검증.
- [ ] 모든 요청 timeout/세션 close가 명시적이며 실패 결과에 provider/date/lot 범위가 포함되도록 한다. error message에는 raw URL/token 없음.

**통과 조건:** provider에서 DB나 Telegram을 import하지 않음. 외부 오류가 빈 성공으로 변환되지 않음. 원래 cooldown key 값이 동일.

## Task 5. Telegram transport·formatter·부분 성공

**생성:** `backend/notifications/{telegram,formatters}.py`; `notifier.py` 대체.

- [ ] HTTP 200 + `{ok:false}`, timeout, invalid JSON, missing credentials, empty batch 테스트.
- [ ] formatters는 문자열/DeliveryBatch만 생성하고 HTTP 호출 없음. KNPS·Parking·KTX readable 내용, TEST prefix, purchase link, 일반실/특실/입석을 검증한다.
- [ ] 20/21 KTX, 30/31 KNPS, 긴 문자열 및 Korean/emoji 포함 메시지를 Telegram 길이 한도 아래로 분할한다. 하나의 항목이 너무 긴 경우 안전한 표시 축약과 key 보존.
- [ ] `TelegramSender.send(batch) -> DeliveryResult` 구현. requests 호출 한 곳, HTTP+JSON 모두 검사, 자동 POST 재시도 없음.
- [ ] raw requests 예외를 print하지 않는다. 로그에 토큰·chat ID가 들어가지 않는 regression test 작성.

**통과 조건:** batch별 결과를 받으며 전체 bool 때문에 부분 성공 항목을 다시 미발송 취급하지 않음.

## Task 6. 공통 알림·모니터 실행 서비스

**생성:** `backend/services/{notifications,checks,jobs}.py`; `app.py` business logic과 `ktx_monitor.py` 대체.

- [ ] NotificationService tests: cooldown 있음/없음, zero, 서로 다른 monitor의 같은 결과, 같은 Telegram 그룹 일부 quiet, inactive, missing channel, batch 1 success/2 fail, history write failure.
- [ ] quiet tests: 작업 제출 시 OFF였다가 실행 시 ON, 조회 중 start 도달, 다음 batch 경계에서 start 도달, latest read 실패, 삭제/채널/options 변경; 차단 항목 이력 0.
- [ ] 07:00 재개 시 과거 미전송 항목을 backlog에서 쏘지 않고 현재 조회 결과만 보내는 것을 검증한다.
- [ ] CheckService가 provider registry와 query cache를 이용하고 per-setting errors를 수집. KNPS 게이트만 선택적으로 적용하고 Modu/KTX는 계속 수행한다.
- [ ] 날짜 policy와 history maintenance를 서비스에 연결. cleanup 31일 이상, 자정 첫 분 1회 규칙, failed maintenance가 성공처럼 기록되지 않도록 한다.
- [ ] CheckRunner는 한 프로세스에서 단일 실행, 중복 submission은 running, executor 앱 소유, graceful shutdown. 기존 KTX import-time executor 제거.
- [ ] 큐에는 전체 secret-bearing settings snapshot을 장기 보관하지 않는다. 실행 시 fresh list, send 시 fresh monitor를 로드한다.
- [ ] CheckSummary에 checked/available/notified/messages/skipped_quiet/errors를 분리. 설정 단위 카운트와 항목/메시지 카운트를 혼동하지 않는다.

**통과 조건:** 모든 카테고리가 같은 정책/이력 경로를 쓰며 한 설정 오류가 다른 설정 실행을 막지 않는다. runner 완료 시간과 실행 결과가 정확히 로그에 남음.

## Task 7. Flask 구성·API 경계

**생성:** `backend/api/{settings,checks,search,errors}.py`; `app.py` 축소.

- [ ] route tests를 HTTP 계약 위주로 작성. providers/repositories module internals에 patch하지 않고 DI fake 사용.
- [ ] 기존 URL/legacy CRUD 메서드 adapter를 보존하되 canonical GET/write는 options 구조를 사용. update unknown field/invalid JSON 400, missing record 404, infra 503, upstream 502/503를 일관화.
- [ ] `/api/check`가 즉시 202 queued / 200 running 반환, 외부 IO를 request thread에서 수행하지 않도록 검증. GET check도 기존 scheduler 호환을 위해 유지.
- [ ] `/api/health`는 liveness를 간단히 유지. 추가 DB 상태를 확인한다면 다른 명시적 readiness 경로를 사용하고 health 호출마다 외부 provider 요청을 하지 않는다.
- [ ] `/api/search` 날짜/범위/길이 검증, 정상 empty []와 upstream error 구분. 현 API 응답 shape는 serializer로 보존.
- [ ] catalogs endpoint와 기존 parking-lots adapter, 공식 stations endpoint 연결. 조회 목록에 비밀 필드 없음.
- [ ] `gunicorn --chdir backend app:app` 및 로컬 app factory가 동작. 운영 workers=1 조건을 명시한다.

**통과 조건:** app.py에 SQL/날짜 순회/알림 formatter/외부 scraping 구현이 없음. 202 계약이 프런트와 문서에 반영됨.

## Task 8. 프런트엔드 전체 모듈화·수면 시간·Quick Search

**파일:** 설계의 `frontend/js/*`, `frontend/css/app.css`, HTML 2개, `tests/categories.spec.ts`, `tests/quiet-hours.spec.ts`, `tests/search.spec.ts`, `tests/fixtures/*`.

- [ ] 기존 intercepted 테스트 fixture를 local JS/CSS 파일까지 제공하도록 먼저 고친다. 실 CDN/실 API는 차단한다.
- [ ] 초기 화면/편집/저장·취소/비활성/카테고리 drag-click/역 모달/알림 이력 버튼의 behavior tests를 보존한 뒤 inline 코드를 모듈로 이동한다.
- [ ] `api.js` 공통 fetch 함수: HTTP/JSON error, 명시적 body, 에러 메시지, pending state; 모든 CRUD의 실패 피드백 통일.
- [ ] form codec은 common fields와 category options만 serialize. 모든 category controls를 먼저 초기화하고 선택 category만 활성화. DOM 전체 checkbox reset 제거.
- [ ] quiet UI: unchecked 기본, 23:00/07:00 표시, checkbox로 두 시간 활성화, 동일 시간 validation, OFF→ON 시간 유지, 다른 monitor 편집값 누출 없음.
- [ ] 목록 카드 quiet-hours 요약, KST 표기, Test Now도 중지 적용된다는 안내. 구현 필드명이나 migration 상태를 사용자 flow에 노출하지 않는다.
- [ ] KNPS 월~일 전체 체크박스와 catalog 데이터 로드. 알 수 없는 기존 선택이 있으면 삭제하지 않고 표시/보존할 수 있게 처리한다.
- [ ] KTX 3 seats, major/region/search/initials/recent stations 보존. localStorage malformed value/사용 불가 대응; Escape 및 focus restore.
- [ ] Quick Search 모듈은 KST 날짜 생성/검증, URLSearchParams, response.ok, safe DOM, empty/error 분리. 두 페이지 CSS/버튼 스타일 공통화.
- [ ] pageerror/unhandledrejection 수집을 테스트에 넣는다. 모바일 폭 및 keyboard navigation 검증, 저장 클릭 연타 중복 요청 방지.

**통과 조건:** 세 category payload에 무관한 필드가 없음. quiet 설정이 저장·새로고침·다른 설정 편집 후에도 정확. upstream text를 HTML로 실행하지 않음.

## Task 9. 죽은 코드·명명·운영 문서 정리

**대상:** 모든 새 모듈 import, 기존 교체 파일, README.md/README.en.md, SYSTEM_DOCUMENTATION.md, FEATURE_DOCUMENTATION.md, QA_CHECKLIST.md, AGENTS.md Repository Map.

- [ ] 새 호출 경로로 완전히 전환된 `db.py`, `scraper.py`, `modu_scraper.py`, `ktx_scraper.py`, `ktx_monitor.py`, `notifier.py`, `settings_model.py`는 제거한다. 단지 옛 테스트를 유지하려고 영구 shim을 남기지 않는다.
- [ ] `rg`로 active 코드에서 user_settings, selected_*, ktx_options, park_name/facility_type DB keys 참조를 점검. legacy API adapter/rollback/fixtures/provider raw fields처럼 필요한 참조는 이유를 명시한다.
- [ ] 더 이상 사용하지 않는 status 함수/UI/polling, 중복 constants, `#XB|`, bare except/pass, global config side effects 정리. 공급자 용어는 해당 provider/formatter 내부에서 유지 가능.
- [ ] backend 함수에는 실제 동작을 표현하는 이름 사용: fetch/query/check/send/record/create/update 구별. setting/monitor 용어는 core에서 monitor로 통일하고 기존 URL은 호환 경계로 남긴다.
- [ ] 의존성을 필요한 것만 남기고 major library upgrade는 섞지 않는다. 스타일 도구를 추가한다면 pyproject에 한 번만 설정, formatter/linter가 대규모 무의미한 변경을 만들지 않도록 적용 범위 통제.
- [ ] SYSTEM_DOCUMENTATION을 schema/API/실행 책임의 상세 기준 문서로 갱신하고 README 두 언어는 핵심 계약·실행·테스트·배포 링크를 정확히 유지한다.
- [ ] FEATURE_DOCUMENTATION에 quiet semantics·3 category·cooldown/자정 예외 설명. QA_CHECKLIST는 이번 실행 증거를 채우는 template로 갱신하고 옛 ALL PASSED를 현재 증거로 두지 않는다.
- [ ] `docs/operations/monitor-refactor-rollout.md`에 실제 cutover/rollback 명령 템플릿, 주체/순서/확인 조건을 쓴다. 실제 credential 값 또는 사용자 데이터는 넣지 않는다.

**통과 조건:** 이름만 바꾼 병렬 legacy/new 구현이 남지 않음. 상세 문서와 코드의 스키마/API/defaults가 일치.

## Task 10. 전체 로컬 검증·자체 리뷰·인계

- [ ] safe backend suite 전체 + 안전한 integration을 새 구조에 맞게 실행. 네트워크 허용 fixture 외 외부 접근 0.
- [ ] mock browser suite 전체 실행. 실제 browser request를 intercept하므로 운영 DB writes 0.
- [ ] disposable PostgreSQL 17 migration forward/rollback/concurrency 검증.
- [ ] 로컬 Supabase/PostgREST + Flask CRUD/UI round-trip 테스트. backend dotenv 자동 운영 연결 차단, provider/Telegram fake. 실제 local URL임을 확인하고 종료 후 생성한 task 전용 자원만 정리.
- [ ] fake provider로 3 category end-to-end 확인: 정상 전송, quiet suppress, 재개, 부분 실패, cooldown. 전송은 fake recorder에만 기록.
- [ ] dependency 방향 리뷰: api→service→domain/repository/provider, domain은 외부 framework 없음. provider는 DB/Telegram 없음, formatter는 HTTP 없음, repository는 Flask 없음.
- [ ] migration/deployment 리뷰: 기존 ID/history 보존, grants 확인, json CHECK SQL NULL, identity sequence, backup/rollback 실제 검증.
- [ ] API/프런트 리뷰: error vs empty, latest monitor policy, KST, same-time validation, category resets, no dead code.
- [ ] `git diff --check`, 변경 목록/잔여 참조 검색. secrets 또는 test artifact가 변경 파일에 없는지 확인.
- [ ] 결과 문서에 명령/버전/실측 결과/미실행 live test/제한을 적고 최종 승인 요청. 테스트 안 한 것을 통과로 표시하지 않는다.

### 실행 명령 기준

기존 안전 명령 (backend 폴더):

```powershell
python -m pytest tests --ignore=tests/test_integration.py
python -m pytest tests/test_integration.py -k "not telegram_test_notification"
```

구조 변경 후에도 동등한 safe default를 제공한다. root에서 실서비스 스크립트까지 수집하는 bare pytest 사용 금지. 새 playwright config의 default는 mock project:

```powershell
npx playwright test --project=mock
pwsh -File scripts/test-local-migration.ps1
git diff --check
```

이 명령들은 **구현 시 만들고 검증할 계약**이며 계획 작성 현재 이미 존재하거나 실행됐다는 뜻이 아니다. local-integration project 명령과 환경 변수는 구현한 fixture에 맞춰 운영 절차서에 확정한다.

## 변경 동작과 보존 동작 체크표

| 반드시 보존 | 명시적으로 수정 |
|---|---|
| 기존 monitor IDs/선택/활성/채널/cooldown/history | 공통 options와 명확한 table/key 이름 |
| KTX 익명 조회·3 seats·역 모달·묶음 알림 | 배열 cache key 오류 |
| KNPS 확률 게이트, Parking/KTX 독립 실행 | 전체 check를 request thread 밖으로 이동 (202 API) |
| cooldown=0일 때 매번 가능·history 생략 | UTC 비교·31일 이상 history cleanup |
| KST 첫 분 일일 이력 초기화 정책 | 같은 날짜 중복 truncate 방지 |
| 기존 provider 정상 데이터 처리·인코딩 | 실패를 빈 결과로 숨기지 않음 |
| 설정 최대 10개 | 원자적 create·identity ID |
| 기존 URL 및 legacy 요청 adapter | 새 canonical DTO, 프런트 safe DOM/error states |

## 다른 모델을 위한 현재 상태와 금지 사항

- 2026-09-22 계획 작성 시 working tree는 clean이었다. 현재 변경은 계획 문서 2개만 의도한다.
- Render CLI 설치/인증과 workspace 선택은 이전 작업에서 완료됐지만 이번 작업에 사용하지 않는다.
- 이전 live commit은 c2aaefc, 이전 완료 migration은 20260921170000. 이번 신규 migration은 **없고 적용하지 않았다**.
- Docker server 28.3.3이 read-only 확인에 응답했다. disposable DB를 만들거나 테스트를 실행하지 않았다.
- 새 로그인·프로젝트 rename·UI framework 교체·분산 queue·사용자 인증 체계 신설은 범위 밖이다. 사용자의 기존 요청에 따라 korail2는 제거하고 코레일 공식 웹의 익명 조회 계약을 직접 구현한다.
- 다음 행동은 사용자 설계/계획 승인 대기다. 승인받지 않고 이 계획을 실행하거나 운영에 반영하지 않는다.

## 최종 배포 승인 문구

구현 후 테스트 증거와 변경사항을 요약한 뒤:

> 로컬 구현·검증을 완료했습니다. 기존 데이터를 이전하는 마이그레이션과 롤백도 로컬에서 검증했습니다. 짧은 점검 시간 동안 확인 작업과 설정 변경을 중지하고, 운영 DB 이전 후 Render 새 버전을 배포해도 될까요? Git 커밋·푸시도 함께 진행할지 확인해 주세요.

사용자가 승인하면 설계 9절과 실행 시 완성된 rollout 문서 순서로 진행한다. 승인 전에는 SQL 적용·Git push·Render deploy를 하지 않는다.
