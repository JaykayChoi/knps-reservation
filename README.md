# KNPS 예약 자동 알림 시스템

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-orange.svg)](https://supabase.com)
[![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-blue.svg)](https://core.telegram.org/bots/api)

국립공원공단(KNPS) 캠핑장 예약 가능 여부를 실시간으로 모니터링하고 사용자 정의 필터와 쿨다운 기간에 따라 Telegram 알림을 보내는 시스템입니다.

> **참고**: 이 시스템은 국립공원공단의 공식 API를 사용하여 캠핑장 예약 가능 여부를 확인합니다. 사용 전 국립공원공단 이용약관을 확인해주세요.

## 🚀 기능

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

---

