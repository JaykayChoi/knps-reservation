# 예약 알림 모니터

국립공원 야영장, 모두의주차장 월정기권, KTX 좌석을 주기적으로 확인하고 설정별 Telegram 채널로 알림을 보냅니다.

## 주요 동작

- 한 모니터는 `knps`, `moduparking`, `ktx` 중 한 카테고리를 가집니다.
- 카테고리별 조건은 공통 `options` JSON 객체에 저장합니다.
- 알림 중지 시간을 모니터별로 켜고 설정할 수 있습니다. 기본값은 꺼짐이며, 시간은 한국 시간 기준입니다.
- 같은 조건의 외부 조회는 한 실행 안에서 한 번만 수행합니다.
- 알림은 여러 결과를 한 메시지로 묶고 Telegram 제한에 맞춰 분할합니다.
- 성공한 메시지 묶음의 항목만 쿨다운 이력에 기록합니다.
- KTX 조회는 로그인을 요구하지 않으며 코레일 공식 웹 조회가 사용하는 익명 시간표 API를 직접 호출합니다.

## 구조

```text
backend/
  api/             Flask 라우트와 이전 payload 호환 경계
  domain/          설정 검증, 시간 정책, 공통 데이터 모델
  notifications/   카테고리별 메시지와 Telegram 전송
  providers/       KNPS, 모두의주차장, 코레일 조회
  repositories/    Supabase 영속 계층
  services/        검사, 알림, 백그라운드 실행과 유지보수
frontend/
  index.html        설정 대시보드
  search.html       KNPS 빠른 조회
  js/               API, 대시보드, 역 선택 모달
supabase/migrations/
scripts/            로컬 마이그레이션 검증과 수동 도구
```

## 설정

Python 3.13 이상과 Node.js 18 이상이 필요합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m pip install pytest pytest-mock
npm ci
```

Render 또는 로컬 환경에 다음 값을 설정합니다.

```text
SUPABASE_URL=
SUPABASE_KEY=
KNPS_USERNAME=
KNPS_PASSWORD=
CHECK_PROBABILITY=0.2
```

KTX 조회에는 아이디와 비밀번호가 필요하지 않습니다. Telegram token과 chat ID는 각 모니터에 저장합니다.

### 로컬 Docker KTX 작업

`backend/.env`에 운영 `SUPABASE_URL`과 `SUPABASE_KEY`를 설정한 뒤 저장소 루트에서
`docker compose up -d --build ktx-worker`를 실행합니다. HTTP 포트나 도메인은 필요하지 않습니다.
작업은 시작 시 한 번, 이후 각 검사가 끝날 때마다 새로 뽑은 2~5분 대기 시간 후 실행됩니다.
매번 활성 KTX 설정만 읽으며, 설정별 알림 중지 시간에는 코레일에 조회 요청을 보내지 않습니다.
코레일 조회가 같은 모니터에서 3회 연속 실패하면 해당 모니터를 자동으로 비활성화합니다.
실패 횟수는 작업 프로세스 메모리에만 유지되므로 컨테이너 재시작이나 정상 조회 시 초기화됩니다.
좌석이 없는 정상 응답과 텔레그램 전송 실패는 이 횟수에 포함되지 않습니다.
기존 알림 이력과 쿨다운을 Supabase에서 공유합니다. 상태 확인은
`docker compose logs -f ktx-worker`, 중지는 `docker compose stop ktx-worker`로 합니다.
다른 환경의 KTX 정기 검사가 계속 켜져 있으면 중복 조회가 발생할 수 있습니다.
웹 서비스의 `/api/check` 정기 검사는 KNPS와 모두의주차장만 실행합니다. KTX는 로컬
Docker 작업만 조회하며, 웹 서비스의 KTX 설정 화면과 수동 검색은 유지됩니다.

## 데이터 모델

`monitor_settings`에는 이름, 카테고리, 활성화 여부, 쿨다운, Telegram 채널, 알림 중지 시간과 `options`가 있습니다.

```json
{
  "name": "추석 연휴",
  "category": "ktx",
  "options": {
    "departure": "서울",
    "arrival": "부산",
    "departure_code": "0001",
    "arrival_code": "0020",
    "date": "2026-10-01",
    "start_time": "08:00",
    "end_time": "18:00",
    "seat_classes": ["general", "special", "standing"]
  },
  "quiet_hours_enabled": true,
  "quiet_hours_start": "23:00",
  "quiet_hours_end": "07:00"
}
```

`notification_history`는 `monitor_id`, `target_date`, `target_key`, `item_key`, `is_waiting`으로 알림 대상을 구분합니다. KTX도 이 공통 이력을 사용합니다. 쿨다운이 0이거나 Test Now 실행이면 이력을 쓰지 않습니다.

## API

- `GET /api/health`: 프로세스 liveness
- `GET /api/settings/all`: 전체 모니터
- `GET /api/settings`: 활성 모니터
- `PUT /api/settings`: 모니터 생성
- `PUT /api/settings/{id}`: 부분 수정
- `POST /api/settings/{id}/duplicate`: 필터·일정·알림 중지 시간·쿨다운·Telegram 정보를 새 모니터로 복제합니다. 이름에 `(copy)`가 붙고 비활성 상태로 생성되며 알림 이력은 복제하지 않습니다.
- `DELETE /api/settings/{id}`: 삭제
- `DELETE /api/settings/{id}/history`: 설정별 이력 삭제
- `DELETE /api/history`: 전체 이력 삭제
- `POST /api/check?test=true`: 백그라운드 검사 요청, `202 queued` 또는 `200 running`
- `GET /api/search`: KNPS 빠른 조회
- `GET /api/parking-lots`: 주차장 catalog
- `GET /api/ktx/stations`: 코레일 공식 역 목록

`/api/ktx/status`와 KTX refresh status 저장 기능은 없습니다.

## 실행과 검증

```powershell
Set-Location backend
python app.py
```

안전한 테스트:

```powershell
Set-Location backend
python -m pytest tests --ignore=tests/test_integration.py
python -m pytest tests/test_integration.py -k "not telegram_test_notification"
Set-Location ..
npx playwright test
.\scripts\test-local-migration.ps1
```

수동 KNPS 실조회는 환경 변수를 설정한 뒤 `python scripts/manual/check-knps.py 20261001`로 실행합니다. 실제 Telegram 통합 테스트는 명시적으로 선택한 경우에만 실행합니다.

## 마이그레이션

`20260922010000_generalize_monitors.sql`은 기존 설정 ID와 데이터를 유지하면서 `user_settings`를 `monitor_settings`로 바꾸고, 카테고리별 컬럼과 `ktx_options`를 공통 `options`로 합칩니다. 알림 중지 시간은 모든 기존 행에서 꺼진 상태로 시작합니다.

운영 적용 전에는 `scripts/db/monitor_refactor_preflight.sql`을 실행하고 백업을 만든 뒤 migration과 `monitor_refactor_verify.sql`을 순서대로 실행합니다. `monitor_refactor_rollback.sql`은 배포 직후 되돌리기 창에서 사용하는 데이터 보존 rollback입니다.
