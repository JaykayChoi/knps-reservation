# 모니터링 시스템 전체 리팩토링 설계

상태: **설계 검토 대기 — 구현 및 운영 반영 미승인**  
작성일: 2026-09-22  
기준 코드: `c2aaefc` (`feat: add standing KTX seat alerts`)

## 1. 목적과 승인 경계

캠핑장 서비스에 기능을 덧붙인 구조를 KNPS·모두의주차장·KTX를 동등하게 지원하는 모니터링 서비스로 정리한다. 유지보수자가 새 카테고리를 추가하거나 알림 규칙을 수정할 때 관련 모듈만 이해하면 되는 구조가 목표다. 기능 추가는 설정별 알림 중지 시간이다.

- 사용자 최종 지시: 계획부터 완성하고 중단한다. 구현은 다른 모델이 담당한다.
- 이 문서와 구현 계획에 대한 승인 전 제품 코드·SQL 마이그레이션을 작성하지 않는다.
- 구현 승인 후에도 로컬 테스트 완료 시 다시 중단하여 **운영 배포와 운영 DB 마이그레이션 승인**을 받는다.
- 이전 대화의 Git/배포 허가는 이번 리팩토링의 자동 배포 허가로 사용하지 않는다. 커밋·푸시도 명시적 요청이 필요하다. Render는 auto-deploy 설정이 있으므로 푸시를 무해한 작업으로 취급하지 않는다.
- `old/`, `.claude/` 설정, 기존 적용 마이그레이션은 변경하지 않는다. 저장소 이름, Render URL, Supabase 프로젝트 이름은 이번 작업에서 변경하지 않는다.
- 계획 수립 중 운영 DB에 접속하지 않았다. 아래 운영 현황은 앞선 작업에서 확인된 기록이며 배포 승인 후 다시 확인해야 한다.

## 2. 현재 코드 감사와 구체적인 문제

| 영역 / 파일 | 현재 구조 또는 문제 | 계획 |
|---|---|---|
| `backend/app.py` | CRUD, DB 직접 삭제, 날짜 생성, 확률 게이트, 이력 정리, 카테고리 실행, 알림 그룹화가 한 파일에 있음 | 앱 구성·라우트와 비즈니스 서비스 분리 |
| `backend/db.py` | 전역 클라이언트, import 시 dotenv 로딩, settings/history/status 혼재, `max(id)+1`, 오래된 컬럼 부재 fallback | 앱 초기화에서 의존성 주입, 저장소 분리, DB identity 및 원자적 생성 |
| `backend/settings_model.py` | KNPS 전용 최상위 필드와 KTX JSON 혼용, 카테고리 전환 시 무관한 필드 초기화 | 공통 모델 + 카테고리별 options 검증기 |
| `backend/ktx_monitor.py` | `tuple(sorted(options.items()))`에 `seat_classes` 리스트가 포함되어 unhashable 오류 가능 | 정규화된 조회 키와 회귀 테스트; 알림 공통 파이프라인 |
| `backend/ktx_monitor.py` | executor/lock이 import 시 생성되고 프로세스 내부에서만 중복 방지 | 앱 수명주기에 속한 bounded runner; 운영 1 worker 조건 명시 |
| `backend/scraper.py` | 날짜 계산과 HTTP가 혼재; 인증 실패/조회 실패가 빈 결과로 반환; 세션 정리 미흡 | KNPS provider와 순수 날짜 정책 분리, 명시적 오류, finally 정리 |
| `backend/modu_scraper.py` | 대상 주차장 2개가 실행 코드에 고정; 오류와 정상 빈 결과가 동일 | 카탈로그 데이터로 이관, provider에 대상 명시 전달, fallback 오류 구분 |
| `backend/ktx_scraper.py` | 익명 조회·역 목록·원본 입석 필드 처리 | 기능 보존, provider 경계로 이동, 원본 응답 파싱 회귀 테스트 강화 |
| `backend/notifier.py` | 카테고리마다 HTTP 구현 중복; KNPS/주차장은 Telegram JSON `ok` 검증 없음; 부분 성공을 bool 하나로 반환 | HTTP sender와 메시지 formatter 분리; 성공 batch별 이력 기록 |
| 알림 이력 | `park_name`, `facility_type`에 주차장/열차 값 저장 | 범용 키 이름으로 변경하되 기존 키 값과 setting 연결 보존 |
| 이력 시간 | cooldown 조회에 naive datetime, 저장은 UTC; 7일 정리와 최대 30일 cooldown 불일치 | UTC 일관화, 정리 보존기간 31일 이상 |
| 자정 초기화 | KST 00:00분 호출마다 전체 truncate 가능 | 기존 일일 초기화 정책 보존, 같은 날짜에는 한 번만 원자적으로 수행 |
| `frontend/index.html` | 한 줄 함수·전역 상태·폼/역 모달/API/CSS 혼재; 전체 checkbox reset; 금·토·일만 표시 | 기능별 JS 모듈, 범위 제한 폼 접근, 월~일 값 손실 방지 |
| `frontend/search.html` | 날짜 로직 중복; 로컬 Date와 UTC ISO 혼용; HTTP 오류를 빈 결과로 오인; 응답 문자열을 HTML 삽입 | 공통 API 클라이언트, KST 날짜 정책, textContent 렌더링 |
| 테스트 | 깊은 Mock 체인/전역 patch, import 시 외부 요청하는 스크립트, E2E가 실제 localhost 설정 수정 가능 | 의존성 주입 fake, 기본 네트워크 차단, 오프라인 UI 테스트·로컬 통합 분리 |
| 문서 | README와 SYSTEM_DOCUMENTATION의 PK 타입/컬럼/API 설명이 실제와 다름; 과거 QA 완료 표시 | README 한·영 유지, 하나의 상세 구조 문서, QA 결과와 체크리스트 분리 |
| 마이그레이션 | 짧은/중복 버전 및 원격·로컬 이력 차이 존재 | 새 14자리 버전만 추가, 역사 재작성·blind db push 금지, 명시적 로컬 baseline |

감사 범위: 활성 backend 8개 모듈, frontend 2개 페이지, backend/tests 전체 테스트 구성과 주요 회귀 테스트, tests의 UI/SQL 테스트, 수동 진단 스크립트, requirements/package 설정, 기존 SQL과 운영 관련 문서. `old/`는 범위 밖이다. 외부 패키지 내부 전체나 현재 운영 스키마를 검사했다고 주장하지 않는다.

## 3. 선택한 접근과 대안

1. **선택: 공통 설정/알림 파이프라인 + 카테고리별 provider.** options 저장·검증 계약은 통일하고, 조회/메시지 차이는 명시적 카테고리 모듈에 둔다. 기존 규모에 맞는 함수·dataclass 중심 구조다.
2. 카테고리마다 테이블을 분리하는 방식은 타입 제약이 쉽지만 사용자가 요청한 공통 JSON 구조와 어긋나고 CRUD/마이그레이션을 반복하게 된다.
3. 범용 플러그인 엔진·Celery/Redis·이벤트 버스로 전면 교체하는 방식은 현재 규모에 불필요하다. 이번에는 도입하지 않는다.

전체 리팩토링은 모든 코드를 무조건 다시 쓰는 뜻이 아니다. 검증된 인코딩 처리, Korail 익명 세션, Modu SSR 파서는 테스트를 붙여 이동하고, 실제 중복/책임 혼재/오류 은폐를 제거한다.

## 4. 최종 저장 모델

### 4.1 `monitor_settings` (기존 `user_settings` rename)

| 컬럼 | 타입 / 규칙 |
|---|---|
| `id` | BIGINT PK, DB 생성 identity; 기존 값 보존, 시퀀스는 현재 최대 ID 다음부터 |
| `name` | TEXT, 공백만 허용하지 않음 |
| `category` | 기존 enum 값 `knps`, `moduparking`, `ktx` 유지 |
| `options` | JSONB NOT NULL, 객체만 허용, 카테고리별 필수 키·타입 검증 |
| `is_active` | BOOLEAN NOT NULL, 기본 true |
| `cooldown_days` | INTEGER NOT NULL, 0~30, 기본 3 |
| `quiet_hours_enabled` | BOOLEAN NOT NULL DEFAULT false |
| `quiet_hours_start` | TIME(0) NOT NULL DEFAULT '23:00'; 분 단위만 허용 |
| `quiet_hours_end` | TIME(0) NOT NULL DEFAULT '07:00'; 분 단위만 허용 |
| `telegram_bot_token`, `telegram_chat_id` | 기존 공통 채널 필드 유지, JSON 옵션에 포함하지 않음 |
| `created_at`, `updated_at` | TIMESTAMPTZ, 기존 시각 보존; 업데이트 시 DB에서 updated_at 갱신 |

`quiet_hours_enabled=true`이면 start != end. start=end를 24시간 중지로 해석하지 않는다. 상시 중지는 is_active로 처리한다. 시간대는 모든 설정에서 Asia/Seoul 고정이며 UI에 명시한다.

카테고리별 조회 조건만 JSON에 넣는다. 자주 공통 조회하는 활성 여부·카테고리·알림 정책·식별자를 하나의 큰 JSON으로 숨기지 않는다. 카테고리별 JSON 구조는 아래와 같고 중첩을 불필요하게 늘리지 않는다.

KNPS:

```json
{"date_mode":"weekday","weeks_ahead":8,"days":["Fri","Sat","Sun"],"start_date":null,"end_date":null,"parks":[],"facility_types":[],"include_waiting":true}
```

Parking:

```json
{"lot_ids":["example-lot-id"]}
```

KTX:

```json
{"departure":"서울","departure_code":"0001","arrival":"부산","arrival_code":"0020","date":"2099-10-01","start_time":"08:00","end_time":"18:00","seat_classes":["general","special"]}
```

KTX station code는 기존 코드 없는 행의 호환을 위해 쌍으로 생략 가능하다. 새 화면은 역 모달을 통해 쌍으로 저장한다. general/special/standing 중 비어 있지 않은 집합으로 정규화한다.

### 4.2 이력·상태·카탈로그

- `notification_history`라는 범용 테이블명은 유지한다.
- `setting_id` → `monitor_id` (BIGINT FK), `park_name` → `target_key`, `facility_type` → `item_key`; `target_date`, `is_waiting`, `sent_at`, `id` 유지. `is_waiting`은 실제 대기 알림 여부라는 명확한 의미이므로 불필요하게 enum으로 바꾸지 않는다.
- `target_date`는 기존 `YYYYMMDD`와 Parking `MONTHLY` 문자열을 보존한다. DATE로 강제 변환하지 않는다.
- KNPS 공원/시설, Parking 주차장명/상품명, KTX 구간/열차·출발시각·seat class의 **기존 key 문자열을 그대로 유지**한다. 더 정밀한 시설 ID로의 변경은 기존 cooldown 의미가 달라지므로 이번 범위에서 제외한다.
- 복합 조회 인덱스: `(monitor_id, target_date, target_key, item_key, is_waiting, sent_at)`; 중복 옛 인덱스는 실행계획/용도를 확인해 정리한다. 이력은 반복 발송을 저장하므로 이 조합에 UNIQUE를 추가하지 않는다.
- `system_status` 유지, 자정 초기화 중복 방지용 `last_history_reset_date DATE NULL` 추가. `last_check_at`은 실제 작업 완료 시각이며 성공 보증이 아니다.
- `monitor_catalog(category, kind, entry_key, label, metadata JSONB)`를 추가한다. `(category,kind,entry_key)` PK. KNPS 공원/시설, Modu 주차장·geohash를 저장하고 현재 목록을 이전용 seed로 보존한다. 사용자의 선택은 options에만 둔다. KTX 역은 공식 목록 API를 계속 사용한다.
- 카탈로그 read API는 토큰/선택 설정을 반환하지 않는다. 이번 작업에 카탈로그 관리 UI는 추가하지 않는다.
- 현재 권한/RLS/GRANT/트리거/FK를 조사하여 rename 후 동일 수준을 보존한다. 권한을 새로 넓히지 않는다.

### 4.3 검증과 업데이트 의미

- 최상위 및 options의 알 수 없는 키, 잘못된 타입, boolean을 숫자로 취급하는 입력, null 객체를 거부한다.
- PATCH와 동등한 기존 PUT 업데이트는 누락된 공통 필드·기존 options를 보존한다. **options를 제공하면 객체 전체 교체**이다. 카테고리를 변경하면 새 options 필수, 이전 조건은 섞지 않는다.
- KNPS days는 Mon~Sun; 0~6 구형 요일은 migration/legacy adapter에서만 변환한다. 기존 빈 days가 실행 시 Fri/Sat/Sun으로 해석되던 행은 migration에서 이 의미를 명시적으로 보존한다. 신규 weekday 설정은 최소 1개 요일 필요; weeks_ahead 0은 날짜 범위 추가분이 없으면 조회 없음.
- KNPS weekday + start/end의 합집합 동작, 절대 날짜 양 끝 포함, 기존 120일 범위 제한은 유지하고 문서화한다. 잘못된 날짜를 조용히 삼키지 않는다.
- 빈 parks/facility_types는 전체, 빈 lot_ids는 조회 없음. 이 차이는 카테고리 검증기와 UI 설명에 둔다.
- 화면·API·DB 기본값을 일치시킨다. 기본 필터 선택은 defaults 모듈/카탈로그에서 공급하며 사용자 선택을 하드코딩하지 않는다.
- DB JSON CHECK는 SQL NULL이 검사 통과로 이어지지 않도록 필수 키/타입을 명시적으로 검사한다. 타입 확인 전에 array_length/cast가 실행될 수 있는 식은 CASE나 검증 함수로 안전하게 구성한다.

## 5. 알림 중지 시간의 정확한 동작

1. 신규 및 모든 기존 설정의 기본은 OFF. 저장·편집·목록에서 개별 설정에 적용한다.
2. 매일 반복, 한국 시간 기준. `[start, end)` — 시작 분부터 중지, 종료 분부터 허용.
3. 예: 23:00~07:00은 23시 이후와 07시 이전 중지. 13:00~14:00도 지원한다.
4. OFF일 때 입력을 disabled 처리하지만 마지막 입력 시간은 저장·복원한다. ON일 때 두 시간 필수, 같은 시간은 사용자에게 오류 표시.
5. 전체 설정 순회/worker 시작 시 정책을 검사해 중지 설정의 조회를 생략한다. 실제 Telegram **각 batch 전송 직전에도 최신 설정과 현재 시각을 다시 읽어** 장시간 조회 중 진입한 중지 시간을 적용한다.
6. 최신 설정이 삭제·비활성화됐거나 category/options/채널이 변경됐으면 해당 이전 snapshot의 미발송 결과를 폐기하고 다음 check에서 재조회한다. 읽기 실패 시 안전하게 전송 중지하고 오류 기록. 전송 직전 이후의 변경까지 원자적 차단을 보장한다고 주장하지 않는다.
7. 중지 때문에 보내지 않은 항목은 sent 이력에 쓰지 않고 cooldown을 시작하지 않는다. 별도 보관·아침 일괄 전송 큐는 만들지 않는다. 종료 후 다음 예약 확인에서 여전히 가능한 결과만 알린다.
8. `Test Now`도 중지 시간을 존중한다. test는 메시지 prefix만 바꾼다. 중지 우회 기능은 만들지 않는다.
9. 같은 Telegram 채널을 쓰는 두 설정 중 하나만 중지돼도 다른 설정은 정상 동작. 그룹화 전에 각 항목의 monitor ownership을 유지한다.
10. Quick Search는 조회만 하므로 quiet hours와 무관하게 사용 가능하다.

## 6. 목표 코드 구조와 계약

```text
backend/
  app.py                         # create_app + app export, routes 등록, DI 조립
  config.py                      # 환경 로딩, timeout/확률/defaults, 테스트 설정
  domain/
    models.py                    # Monitor, Availability, HistoryKey, QueryResult, DeliveryBatch
    settings.py                  # 공통 필드 + category options validation
    clock.py                     # Clock, UTC/KST 변환
    schedules.py                 # KNPS 날짜 계산
    notification_policy.py       # active/quiet-hours/cooldown 정책
  providers/
    knps.py                      # 인증/인코딩/응답→Availability
    moduparking.py                # pins/SSR fallback/응답→Availability
    ktx.py                       # 익명 조회/페이지/입석/역 목록
    registry.py                  # category→provider 매핑 (고정된 작은 dict)
  repositories/
    client.py                    # Supabase 생성, 설정 오류
    monitors.py                  # CRUD, atomic creation RPC, latest snapshot
    history.py                   # cooldown, batch history, maintenance
    catalogs.py                  # 카탈로그 읽기
    status.py                    # last check
  services/
    checks.py                    # 카테고리 dispatch, query cache, errors/results
    jobs.py                      # 공통 bounded background runner
    notifications.py             # policy→cooldown→batch→send→history
  notifications/
    telegram.py                  # HTTP 송신 한 곳, safe errors
    formatters.py                # 카테고리별 메시지, 순수 함수
  api/
    settings.py                  # existing URL CRUD, DTO serialization
    checks.py                    # /api/check
    search.py                    # /api/search, catalogs, stations
    errors.py                    # 일관된 error→HTTP 매핑
    legacy_settings.py           # 구형 요청만 변환하는 명시적 한시 어댑터
  tests/                         # domain/providers/repositories/services/api 단위로 정리
frontend/
  index.html, search.html         # semantic markup만
  css/app.css                    # 두 페이지 공통 스타일
  js/api.js                      # fetch/error/JSON 계약
  js/ui.js                       # toast, safe DOM, modal focus
  js/dashboard.js                # 목록·이벤트 orchestration
  js/monitor-form.js             # 공통 폼·카테고리별 codec
  js/station-picker.js            # 역 모달·최근 역
  js/search.js                   # Quick Search
```

이 구조는 역할을 명확히 하는 기준이다. 내용이 몇 줄이고 별도 변화 이유가 없는 파일을 추가로 쪼개지 않는다. Flask/vanilla JS/Tailwind를 유지하고 빌드 도구나 ORM/DI 프레임워크를 도입하지 않는다. 기존 `gunicorn --chdir backend app:app` 실행을 보존한다.

### 주요 인터페이스

- `normalize_monitor(payload, existing=None) -> MonitorInput`: 순수 검증, DB/환경에 접근하지 않음.
- `Clock.now() -> aware datetime`: production UTC; 테스트 fake clock. 날짜 판단은 KST로 변환.
- `is_quiet_time(monitor, now) -> bool`: 순수 정책 함수.
- `Provider.fetch(options, context) -> QueryResult`: stateless. context는 clock, HTTP factory, catalog, 실행 범위 cache. 반환값에 items와 조회 단위 errors를 분리.
- `Availability`: category, target_date, target_key, item_key, is_waiting, 표시용 details. 공급자 raw JSON을 공통 서비스로 흘리지 않는다.
- `HistoryKey`: monitor_id + 기존 4개 식별 값. 화면용 이름과 저장 key를 분리한다.
- `MonitorRepository.list_active/get/create/update/delete`, `HistoryRepository.is_on_cooldown/record_batch`, `CatalogRepository.list`, `StatusRepository.record_check`.
- `NotificationService.deliver(monitors, results, test_mode) -> DeliverySummary`: 소유 설정 유지, 전송 직전 재검사, 성공 batch만 기록.
- `CheckService.run(test_mode=False) -> CheckSummary`, `CheckRunner.submit(test_mode=False) -> JobAcceptance`.

JSON 정규화 후 조회 키는 provider에서 정한 조회 관련 필드의 immutable tuple 또는 안정된 JSON 직렬화로 만든다. 리스트 순서가 의미 없는 seat_classes는 정렬/중복 제거한다. 토큰·채팅 ID·quiet hours는 조회 캐시 키에 넣지 않는다. cache 수명은 실행 1회이고 무기한 재사용하지 않는다.

## 7. 실행·오류·알림 전달

- `/api/check`는 모든 카테고리를 공통 runner로 제출하고 즉시 202를 반환한다. 진행 중 호출은 200 + running; 대기열을 누적하지 않는다. 실제 실행 시 DB에서 설정을 읽는다.
- 이전 KTX만의 executor는 제거한다. 앱 종료 시 runner를 정리한다. 실질적 다중 worker/distributed exactly-once 보장은 범위 밖; Render 한 프로세스 한 worker 조건을 문서·실행 설정으로 고정한다. worker를 늘리려면 공유 lease/queue 설계가 별도 필요하다.
- KNPS KST 00~01시 외 확률 게이트는 유지하고 KNPS에만 적용한다. Parking/KTX는 그 게이트와 무관하다. 설정별 오류가 다음 설정/카테고리 실행을 중단하지 않게 한다.
- 기존 check 응답의 완료 count를 즉시 반환할 수 없다는 API 변경을 문서화하고 화면은 '확인 요청됨/진행 중'만 표시한다. KTX refresh status UI를 다시 만들지 않는다. 완료 요약은 구조화 로그와 기존 last_check_at에 둔다.
- 정상 빈 결과와 인증/네트워크/파싱 실패를 구별한다. partial query 결과는 성공 항목과 오류 범위를 함께 보존한다. 잘못된 응답을 빈 성공으로 바꾸지 않는다.
- Telegram transport는 HTTP 상태와 JSON `ok`를 모두 검사한다. formatter는 JSON/HTTP를 모른다. 기본 plain text로 마크다운 escaping 문제를 줄인다.
- 메시지는 카테고리·채널·필요한 구간/날짜로 그룹화하고 KTX 최대 20개, KNPS 최대 30개 항목 + Telegram 길이 한도를 함께 지킨다. provider 문자열이 길어도 한도를 넘지 않도록 표시 항목을 안전하게 줄인다.
- batch 성공 직후 그 batch의 해당 설정 이력만 저장한다. 다음 batch 실패가 이전 성공을 지우지 않는다. cooldown=0은 조회/기록 생략 동작 유지.
- 시간초과처럼 Telegram 수신 여부가 불명확한 실패에 자동 POST 재시도를 추가하지 않는다. Telegram과 DB는 하나의 트랜잭션이 아니므로 send 성공 후 history 실패 시 재알림 가능성이 남는다는 한계를 로그와 문서에 기록한다.
- 오류 응답/로그에 token, chat ID, Supabase key, 인증 URL, raw 예외 request를 넣지 않는다. 사용자 메시지는 정해진 error code + 안전한 설명, 내부 로그는 범주·monitor ID·예외 타입·카운트 중심.
- 자정 초기화 정책은 삭제하지 않는다. KST 00:00분 안에서 `last_history_reset_date`와 이력 초기화를 DB transaction/lock으로 묶어 날짜당 1회만 수행한다. 기존 자정 정책이 여러 날 cooldown을 리셋한다는 점도 명시한다.

## 8. API·프런트엔드

- 기존 `/api/settings` 및 `/api/settings/<id>`, `/api/settings/all`, `/api/history`, `/api/parking-lots`, `/api/ktx/stations`, `/api/search`, `/api/health` URL은 유지한다.
- 현재 PUT collection=create, POST collection=첫 active update의 특이한 계약은 한시 route adapter로 보존·deprecated 표시한다. 프런트엔드는 ID 지정 업데이트만 사용한다. 이름 정리만을 위해 사용 중인 호출을 갑자기 바꾸지 않는다.
- GET/새 화면 write는 canonical options 및 quiet_hours 필드만 사용한다. 구형 top-level selected_* / ktx_options 입력은 `legacy_settings.py`에서만 변환. canonical과 legacy를 동시에 보내면 400. core 코드에 이중 모델이 남지 않는다.
- `/api/search`는 기존 KNPS 조회 응답을 serializer로 보존; 잘못된 날짜 400, upstream 실패 502/503, 정상 빈 결과 200 []. query string은 URLSearchParams로 생성한다.
- `/api/catalogs/<category>`는 공원/시설/주차장 선택 데이터와 안전한 defaults를 제공; 기존 parking-lots는 adapter로 유지한다.
- 폼은 공통 정보·알림 정책·카테고리 조건을 분리한다. quiet-hours OFF 시 시간 입력 disabled; 요약 카드에 활성 시간 범위를 표시한다.
- 옵션 DOM 선택자는 해당 form/section에 한정, 새 설정→다른 설정 편집 시 stale 상태 누출 방지. 카테고리 변경이 공통 quiet-hours/토큰/쿨다운을 초기화하지 않게 한다.
- 역 모달 주요역/지역/초성/최근 역, 코드·이름 동시 저장을 보존한다. localStorage 값의 타입과 접근 실패를 처리한다. modal escape/focus 복귀를 구현한다.
- 두 HTML의 inline JS/CSS를 공통 파일로 이동하고 ES modules로 연결한다. mock UI 테스트는 JS/CSS 요청까지 실제 로컬 파일로 제공해야 한다.
- KST 날짜 생성과 결과 렌더링을 테스트한다. API 데이터는 textContent/DOM API로 표시한다. Quick Search error와 empty state를 분리한다.

## 9. 데이터 이전과 롤백 전략

최종적으로 legacy 컬럼을 영구 이중 보관하지 않는다. schema rename/drop이 구버전 서버를 깨뜨리므로 **승인된 짧은 점검 시간에 원자적 cutover**를 선택한다. 구현을 단순하게 유지하면서 운영 데이터 손실을 방지한다. 무중단 dual-write/view-trigger 교량을 즉석에서 추가하지 않는다.

### 로컬에서 준비할 산출물

- 신규 14자리 forward migration, rollback SQL(자동 적용 migrations 폴더 밖), migration fixture/assertions, schema preflight/validation SQL, 절차서.
- 실제 row를 삭제하지 않고 테이블 rename·options backfill·키 rename·identity 추가. 기존 ID, timestamps, name, active, cooldown, credentials, history rows/FK 유지.
- KTX legacy either→[general,special], general→[general], special→[special]. standing을 임의로 켜지 않는다. 이미 배열인 값은 보존한다.
- NULL/비정상 기존 값은 사전 검증에서 검출한다. 의미가 불분명한 row를 defaults로 덮어쓰지 않고 배포를 중단한다. 진단에 비밀값을 출력하지 않는다.
- 옛 컬럼 drop 전에 JSON과 원본의 category별 동등성을 검증하고, 실패하면 전체 rollback. category_filter_exclusivity를 새 옵션 제약으로 대체.
- 삭제/생성 race를 막는 생성 RPC는 transaction advisory lock 아래 10개 제한과 INSERT 수행; identity 사용. 새 RPC 권한은 기존 서버 역할에만 필요한 만큼 부여.
- 모니터 이력 FK 타입을 BIGINT로 정렬하고 rename된 테이블을 참조하는지 검증. RLS/GRANT/함수의 참조/인덱스까지 검사.

### 배포 승인 후에만 실행할 순서

1. remote schema/migration history 및 Render commit을 읽기 확인한다. 기존 원격-only `20260330085629`, `20260804154110` 등 이력 차이를 재확인한다. 이번 변경을 이유로 전체 역사 repair/reset을 하지 않는다.
2. schema+설정+history+status+카탈로그 및 grants를 보호된 backup으로 보관하고 복원 가능성을 확인한다. 비밀 데이터 backup은 Git/로그에 포함하지 않는다.
3. 실제 cron 호출 주체를 파악해 잠시 정지하고, 설정 writes/manual check도 차단한다. 진행 중 worker가 끝났는지 확인한다. 종료 확인 없이 rename/drop하지 않는다. 이 경로를 확보하지 못하면 배포 차단 사유다.
4. 단일 transaction으로 신규 SQL과 정확한 migration 기록을 적용한다. Management API가 필요한 경우에도 schema 변경과 이력 INSERT를 같은 transaction에 둔다. 버전만 기록하고 실제 SQL을 누락하지 않는다.
5. 검증된 새 커밋을 Render에 배포하고 live 성공을 확인한다. 구버전 코드가 새 schema에서 요청을 받는 동안 외부 호출은 차단 상태다.
6. schema/data 비교, health, 설정 read, 새 정적 자산 확인. 실 Telegram 테스트는 배포 승인이 메시지 발송까지 포함하는지 확인하고 별도로 다룬다.
7. 차단/cron을 해제하고 모니터링한다. 원래 스케줄을 정확히 복원한다.

### 롤백

- 배포 실패 시 요청 차단 유지 → transaction rollback SQL로 원래 schema/fields 재구성 → 이전 앱 commit 배포 → 검증 → 호출 재개.
- 새 앱에 writes가 허용되기 전 롤백을 기본 안전 창으로 둔다. writes 허용 이후에는 단순 옛 백업 restore로 신규 데이터를 지우지 않는다. 현재 canonical rows를 역변환하는 별도 forward-fix/rollback이 필요하다.
- quiet-hours는 구버전 앱이 지원하지 않는다. 설정 값은 보호 backup에 보존하고 구버전 복귀 시 기능 불가를 알린다.
- rollback SQL은 새 legacy columns 재구성, ID sequence/default 복구, FK/index/constraint/grants 복구를 포함하며 로컬 round-trip으로 검증한다.

## 10. 검증 및 완료 기준

운영 리소스를 쓰지 않는 검증만 구현 승인 범위에 포함된다.

- domain 테스트: JSON 검증, 부분 갱신, 카테고리 전환, 기본값, quiet-hours 양 끝/자정/UTC→KST, 날짜·시간 범위.
- service 테스트: 중지 시 발송·이력 없음, 재개 후 알림, 조회 중 quiet 시작, 최신 설정 비활성/삭제/변경, 같은 채널 혼합, batch 부분 실패, cooldown=0, 이력 실패, 카테고리 오류 격리, 캐시 배열, 중복 job.
- provider 테스트: KNPS 인증/인코딩/null/error/session close, Modu pins/SSR/unknown catalog, Korail 익명/session/timeouts/pagination/standing raw field.
- repository/SQL 테스트: ID·FK·history 보존, 옛/새 KTX 배열, JSON CHECK null loophole, concurrent creation 10개 제한, timestamp/timezone, migration 실패 원자성, rollback round-trip, 자정 1회.
- UI 테스트: 세 카테고리 신규/편집/전환, quiet-hours OFF/ON/자정/동일 시간 오류, 입력 복원, API 오류, modal keyboard, 역 모달, 요청 body에 options만, Quick Search dates/오류/HTML 문자열.
- 로컬 PostgreSQL 17 컨테이너는 localhost에만 바인딩하고 fake 데이터만 사용. 기존 Supabase local config나 사용자의 DB를 reset하지 않는다. PostgreSQL SQL 통과와 PostgREST 통합 통과를 구분해 보고한다.
- 실제 Flask+로컬 Supabase/PostgREST CRUD smoke도 수행한다. 모든 외부 provider/Telegram은 fake transport로 대체한다. 임시 로컬 환경을 마련하지 못하면 완전 검증이라고 보고하지 않는다.
- pytest와 Playwright 기본 실행은 외부 네트워크/실서비스 mutation을 차단한다. 기존 live integration은 명시적 opt-in으로 격리한다.
- README 한·영, SYSTEM_DOCUMENTATION, FEATURE_DOCUMENTATION, QA_CHECKLIST를 새 계약과 맞춘다. 과거 QA 통과 표시를 이번 통과 근거로 재사용하지 않는다.

완료 시 전달물: 변경 파일/구조, 동작 보존 및 수정 목록, 실제 테스트 명령·결과, SQL 이전/역변환 결과, 알려진 제한, 정확한 배포 대상/순서, **운영 반영 승인 질문**. 승인 전 commit/push/deploy/remote migration은 하지 않는다.
