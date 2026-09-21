# KNPS 예약 자동 알림 시스템

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-orange.svg)](https://supabase.com)
[![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-blue.svg)](https://core.telegram.org/bots/api)

국립공원공단(KNPS) 캠핑장 예약 가능 여부를 실시간으로 모니터링하고 사용자 정의 필터와 쿨다운 기간에 따라 Telegram 알림을 보내는 시스템입니다.

> **참고**: 이 시스템은 국립공원공단의 공식 API를 사용하여 캠핑장 예약 가능 여부를 확인합니다. 사용 전 국립공원공단 이용약관을 확인해주세요.

## 🚀 기능

- **카테고리별 설정**: 편집 모달 상단에서 KNPS, Parking, KTX 버튼을 클릭하거나 선택 영역으로 드래그합니다. 설정 하나는 한 종류만 감시합니다.
- **KTX 좌석 알림**: 출발역·도착역, 탑승일, 출발 시간 범위(양 끝 포함), 일반실·특실·둘 다를 선택합니다. 성인 1명 좌석 기준이며 예약은 코레일톡에서 진행합니다.

### 카테고리 마이그레이션 및 KTX 설정

배포 전에 기존 DB를 백업하고 이전 마이그레이션 이후
`supabase/migrations/20260921120000_setting_categories_ktx.sql`을 적용하세요.
`setting_category` enum(`knps`, `moduparking`, `ktx`)과 `ktx_options`가 추가됩니다.
이어서 `20260921160000_remove_ktx_status.sql`을 적용합니다. 주차장이 들어 있는 기존 설정마다 별도
Parking 설정을 만들고 `MONTHLY` 알림 이력을 옮깁니다. 원래 설정에는 KNPS 필터와
이력이 남습니다. 활성 상태·텔레그램 설정·쿨다운을 보존하며, 분리 결과가 일반적인
설정 생성 한도 10개를 넘어도 데이터를 버리지 않습니다. 분리 후 필요 없는 KNPS
설정은 비활성화하세요.

`backend/requirements.txt`를 설치하면 별도 코레일 계정 없이 익명으로 좌석을 조회합니다.
역 선택기는 코레일 공식 역 목록을 사용하며 이름 직접 입력을 허용하지 않습니다.
[고정 버전 korail2 클라이언트](https://github.com/dhfhfk/korail2/tree/4b134266fff097ea0fd54e9f760cb128b6c8f878)를
읽기 전용으로 사용합니다. 코레일 변경이나 네트워크 오류는 조회 실패로 기록됩니다.

기존 스케줄러에서 `/api/check`를 계속 호출하면 됩니다. KTX와 Parking은 KNPS 확률
게이트와 무관하게 실행됩니다. KTX는 백그라운드 스레드에서 실행하며 응답에
`ktx.status`(`queued`, `running`, `no_active_settings`)가 포함됩니다.
별도의 KTX 상태 저장이나 새로고침 화면은 없습니다. **Test Now는 실제 텔레그램 메시지를 발송합니다.** KTX는 작업 완료 후
발송될 수 있습니다. 자동 예약은 하지 않습니다.

지속 실행되는 Python 서버에서 **워커 프로세스 1개**로 운영하세요. 예를 들어
`backend/`에서 `gunicorn --workers 1 --threads 4 app:app`을 실행합니다. 중복 실행 방지는
프로세스 단위이므로 다중 워커·다중 서버나 요청 종료 시 작업이 중단되는 서버리스
환경에는 적합하지 않습니다. 각 요청에 연결·응답 시간 제한이 있고 조회는 최대 40페이지로
제한합니다(초과하면 시간 범위를 좁혀 주세요). KTX 이력은 날짜·노선·열차 번호·출발 시각·좌석
등급을 구분하며 발송 성공 후에만 기록합니다. 한 번의 조회에서 나온 좌석은 Telegram 메시지 하나로
묶고, 메시지 길이를 제한하기 위해 20건을 넘을 때만 나눕니다. 쿨다운 0은 반복 알림이며 기존 자정
이력 초기화도 유지됩니다.

설정 API는 `category`, `ktx_options`를 받습니다. 부분 수정 시 기존 카테고리를 보존하고,
카테고리를 변경하면 관련 없는 필터를 비웁니다. KTX 옵션 예시:

```json
{"departure":"서울","departure_code":"0001","arrival":"부산","arrival_code":"0020","date":"2026-10-01","start_time":"08:00","end_time":"18:00","seat_class":"either"}
```

외부 요청 없이 화면 검증: `npx playwright test tests/categories.spec.ts`.
백엔드는 `backend/`에서 `python -m pytest tests --ignore=tests/test_integration.py`와
`python -m pytest tests/test_integration.py -k "not telegram_test_notification"`를 실행합니다.

- **실시간 모니터링**: 국립공원공단 캠핑장 예약 가능 여부를 24시간 모니터링
- **스마트 알림**: 사용자가 설정한 조건에 맞는 예약 가능 시 Telegram으로 즉시 알림
- **쿨다운 관리**: 동일한 예약 정보에 대한 알림 스팸 방지를 위한 쿨다운 설정
- **웹 대시보드**: 직관적인 한국어 UI로 설정 관리 및 예약 현황 확인
- **자동화된 테스트**: pytest를 활용한 안정적인 코드 품질 보장
- **로컬 개발 환경**: Docker 기반 Supabase로 손쉬운 로컬 개발
- **다중 날짜 범위 지원**: 원하는 기간 내 예약 가능 여부 필터링

## 🏗️ 아키텍처

```
knps-reservation/
├── backend/          # Python/Flask API 서버 및 코어 로직
│   ├── app.py        # API 진입점 및 라우터
│   ├── db.py         # Supabase 인터페이스 (설정 및 기록)
│   ├── scraper.py    # KNPS API 상호작용 로직
│   └── notifier.py   # Telegram 알림 서비스
├── frontend/         # 웹 기반 설정 대시보드
│   └── index.html    # Vanilla JS + Tailwind CSS UI
└── supabase/         # 데이터베이스 마이그레이션 및 설정
```

## 🛠️ 기술 스택

### 백엔드
- **Python 3.13+** - 코어 프로그래밍 언어
- **Flask** - API 엔드포인트를 위한 웹 프레임워크
- **Supabase** - 실시간 기능을 갖춘 PostgreSQL 데이터베이스
- **Requests** - KNPS API 상호작용을 위한 HTTP 클라이언트
- **Telegram Bot API** - 알림 전송

### 프론트엔드
- **Vanilla JavaScript** - 프레임워크 의존성 없음
- **Tailwind CSS** - 유틸리티 퍼스트 CSS 프레임워크
- **네오브루탈리스트 디자인** - 대담하고 기능적인 UI 디자인

### DevOps
- **Docker** - 로컬 Supabase 개발
- **pytest** - 포괄적인 테스트 프레임워크
- **Playwright** - end-to-end 브라우저 테스트

### 제작 도구
- **OpenCode** - Agentic AI 개발 플랫폼
- **Oh-My-OpenCode** - OpenCode 플러그인

## 📦 설치

### 필수 조건
- Python 3.13 이상
- Node.js 18+ (Supabase CLI용)
- Docker (로컬 Supabase용)
- Telegram Bot Token ([@BotFather](https://t.me/botfather)에서 발급)

### 백엔드 설정

1. 저장소 클론:
```bash
git clone <repository-url>
cd knps-reservation
```

2. Python 환경 설정:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. 환경 변수 설정:
프로젝트 루트에 `config.ini` 파일 생성:
```ini
[telegram]
bot_token = YOUR_TELEGRAM_BOT_TOKEN
chat_id = YOUR_TELEGRAM_CHAT_ID

[supabase]
url = YOUR_SUPABASE_URL
key = YOUR_SUPABASE_ANON_KEY
```

### 데이터베이스 설정

1. 로컬 Supabase 시작:
```bash
cd supabase
supabase start
```

2. 마이그레이션 적용:
```bash
supabase db reset
```

### 프론트엔드 설정
프론트엔드는 별도의 빌드 과정이 필요 없는 단일 HTML 파일입니다.
백엔드 서버를 실행하면 `http://localhost:5000`에서 접속 가능하며, 직접 `frontend/index.html` 파일을 브라우저에서 열어도 동작합니다.

## 🚀 사용 방법

### 애플리케이션 시작

1. 백엔드 서버 시작:
```bash
cd backend
python app.py
```

2. 프론트엔드 대시보드 열기:
- `http://localhost:5000`으로 이동 (백엔드가 프론트엔드 제공)
- 또는 브라우저에서 직접 `frontend/index.html` 열기

### 설정

1. **Telegram 설정**:
   - [@BotFather](https://t.me/botfather)에서 봇 토큰 발급
   - 봇에게 메시지를 보내 채팅 ID 확인
   - 둘 다 `config.ini`에 추가

2. **필터 설정**:
   - 모니터링할 공원 선택
   - 시설 유형 선택 (오토캠핑, 카라반 등)
   - 쿨다운 기간 설정 (알림 간격 일수)
   - 예약 가능 여부 확인 날짜 범위 정의

### API 엔드포인트

| 메소드 | 엔드포인트 | 설명 |
|--------|----------|-------------|
| GET | `/api/settings` | 현재 사용자 설정 조회 |
| POST | `/api/settings` | 사용자 설정 업데이트 |
| POST | `/api/check` | 수동 예약 가능 여부 확인 (TEST 접두사) |
| GET | `/api/history` | 알림 기록 조회 |


## 🧪 테스트

### 테스트 실행

```bash
cd backend
pytest
```

### 테스트 범위

- **단위 테스트**: 데이터베이스 작업, 스크래핑 로직, 알림 포맷팅
- **통합 테스트**: Flask 엔드포인트, Telegram 알림
- **엔드투엔드 테스트**: Playwright를 활용한 브라우저 자동화

### 테스트 구조

```
backend/tests/
├── test_db.py          # 데이터베이스 작업 테스트
├── test_scraper.py     # 스크래핑 로직 테스트
├── test_notifier.py    # 알림 포맷팅 테스트
└── test_integration.py # 통합 테스트
```

## 📊 데이터베이스 스키마

### 테이블

#### `user_settings`
| 컬럼 | 타입 | 설명 |
|--------|------|-------------|
| id | UUID (기본 키) | 고유 식별자 |
| parks | JSONB | 모니터링할 공원 이름 배열 |
| facility_types | JSONB | 확인할 시설 유형 배열 |
| cooldown_days | INTEGER | 알림 간격 일수 |
| start_date | DATE | 예약 가능 여부 확인 시작 날짜 |
| end_date | DATE | 예약 가능 여부 확인 종료 날짜 |
| created_at | TIMESTAMP | 레코드 생성 시간 |

#### `notification_history`
| 컬럼 | 타입 | 설명 |
|--------|------|-------------|
| id | UUID (기본 키) | 고유 식별자 |
| identifier | TEXT | 고유 알림 키 (YYYYMMDD_공원_시설) |
| sent_at | TIMESTAMP | 알림 전송 시간 |
| park_name | TEXT | 공원 이름 |
| facility_type | TEXT | 시설 유형 |
| available_dates | JSONB | 예약 가능 날짜 배열 |

#### `system_status`
| 컬럼 | 타입 | 설명 |
|--------|------|-------------|
| id | UUID (기본 키) | 고유 식별자 |
| last_check_at | TIMESTAMP | 마지막 시스템 확인 시간 |
| updated_at | TIMESTAMP | 마지막 업데이트 시간 |

## 🔧 배포

### 프로덕션 고려사항

1. **환경 변수**: 프로덕션 Supabase 자격 증명 사용
2. **프로세스 관리**: gunicorn 또는 유사한 WSGI 서버 사용
3. **크론 작업**: 시스템 cron 또는 Celery를 사용한 정기적 확인 예약
4. **모니터링**: 로깅 및 헬스 체크 구현
5. **보안**: Telegram 토큰과 Supabase 키 안전하게 보관

### Docker 배포

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```


## 📄 라이선스
이 프로젝트는 MIT 라이선스 하에 있습니다. 자세한 내용은 LICENSE 파일을 참조하세요.

### 자정 알림 기록 초기화

백엔드 변경을 배포하기 전에 `supabase/migrations/20260921_truncate_notification_history.sql`을 적용하세요. 한국시간 00:00:00~00:00:59에 들어온 `/api/check` 요청은 가용 여부 확인 전에 `notification_history`를 비웁니다. 데이터베이스 함수는 이 시간대 밖의 호출을 거부합니다. `cooldown_days`가 `0`인 설정은 알림을 보내도 기록을 저장하지 않습니다.

---

