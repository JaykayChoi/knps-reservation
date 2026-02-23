# KNPS Reservation Auto-Notification System - 시스템 문서화

## 📋 시스템 개요

**KNPS Reservation Auto-Notification System**은 한국 국립공원공단(KNPS) 캠핑장 예약 가능 여부를 실시간으로 모니터링하고, 사용자 정의 필터와 쿨다운 기간에 따라 Telegram 알림을 전송하는 자동화 시스템입니다.

### 핵심 기능
- 다중 설정 관리: 최대 10개의 독립적인 모니터링 설정
- 실시간 예약 가능성 확인
- Telegram 실시간 알림
- 사용자 정의 필터링 (공원, 시설 유형, 요일)
- 중복 알림 방지를 위한 쿨다운 시스템

---

## 🏗️ 시스템 아키텍처

### 디렉토리 구조
```
knps-reservation/
├── backend/              # Python/Flask 백엔드 서버
│   ├── app.py           # API 엔드포인트 및 라우터
│   ├── db.py            # Supabase 데이터베이스 인터페이스
│   ├── scraper.py       # KNPS API 상호작용 로직
│   └── notifier.py      # Telegram 알림 서비스
├── frontend/            # 웹 기반 설정 대시보드
│   └── index.html       # Vanilla JS + Tailwind CSS UI
└── old/                 # 레거시 모놀리식 참조 코드
```

### 기술 스택
- **백엔드**: Python 3.x, Flask, Supabase (PostgreSQL)
- **프론트엔드**: Vanilla JavaScript, Tailwind CSS
- **데이터베이스**: Supabase (PostgreSQL 호환)
- **알림**: Telegram Bot API
- **테스트**: pytest, Playwright

---

## 🔧 백엔드 시스템

### 1. 데이터베이스 스키마

#### `user_settings` 테이블
```sql
CREATE TABLE user_settings (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    date_mode VARCHAR(20) DEFAULT 'weekday',  -- 'weekday' 또는 'absolute'
    weeks_ahead INTEGER DEFAULT 4,
    start_date DATE,
    end_date DATE,
    cooldown_days INTEGER DEFAULT 1,
    telegram_bot_token TEXT,
    telegram_chat_id TEXT,
    selected_days TEXT[],      -- ['Fri', 'Sat', 'Sun']
    selected_types TEXT[],     -- ['특화야영장', '카라반', '자동차야영장']
    selected_parks TEXT[],     -- 한국 국립공원 이름 배열
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### `notification_history` 테이블
```sql
CREATE TABLE notification_history (
    id SERIAL PRIMARY KEY,
    setting_id INTEGER REFERENCES user_settings(id),
    notification_key VARCHAR(255) UNIQUE,  -- YYYYMMDD_ParkName_FacilityType
    sent_at TIMESTAMP DEFAULT NOW()
);
```

### 2. API 엔드포인트

#### 설정 관리
- `GET /api/settings/all` - 모든 설정 조회
- `GET /api/settings/{id}` - 특정 설정 조회
- `POST /api/settings` - 새 설정 생성
- `PUT /api/settings/{id}` - 설정 업데이트
- `DELETE /api/settings/{id}` - 설정 삭제

#### 시스템 동작
- `POST /api/check` - 수동 확인 트리거
- `POST /api/check?test=true` - 테스트 모드 확인

### 3. 스크래핑 로직

#### KNPS API 상호작용
- **엔드포인트**: `selectCampRemainSiteList.do`
- **인코딩**: EUC-KR / UTF-8 (엔드포인트에 따라 다름)
- **데이터 처리**: JSON 파싱 및 필터링
- **에러 처리**: 모든 API 호출은 try-except 블록으로 래핑

#### 날짜 계산 로직
- **평일 모드**: 현재부터 N주 앞의 특정 요일(Fri/Sat/Sun) 계산
- **절대 날짜 모드**: 지정된 시작-종료 날짜 범위
- **쿨다운**: 동일 예약 가능성에 대한 중복 알림 방지

### 4. 알림 시스템

#### Telegram 통합
- Bot Token 및 Chat ID 기반 인증
- 메시지 포맷팅: 공원명, 시설 유형, 날짜, 예약 링크 포함
- 테스트 모드: `[TEST]` 접두사로 구분
- 에러 처리: 네트워크 실패 시 재시도 및 로깅

---

## 🎨 프론트엔드 시스템

### 1. 사용자 인터페이스

#### 대시보드 뷰
- **설정 카드 그리드**: 각 설정의 상태 표시
- **활성화/비활성화 토글**: 실시간 상태 변경
- **편집/삭제 기능**: 설정 관리
- **빈 상태 처리**: 설정이 없을 때 안내 메시지

#### 설정 모달 폼
- **기본 정보**: 설정명, 활성화 상태
- **일정 설정**: 평일 모드 vs 절대 날짜 모드
- **시설 유형 필터**: 특화야영장, 카라반, 자동차야영장
- **국립공원 선택**: 21개 한국 국립공원 체크박스
- **Telegram 통합**: Bot Token, Chat ID 입력
- **쿨다운 설정**: 알림 간 최소 간격

### 2. 폼 데이터 흐름

#### 데이터 로딩 (Edit)
```javascript
// 문제 해결: 문자열/숫자 비교 버그 수정
// 변경 전: s.id === settingId (엄격한 비교)
// 변경 후: s.id == settingId (느슨한 비교)
const setting = settingsList.find(s => s.id == settingId);
```

#### 폼 채우기 로직
```javascript
function populateForm(data) {
    // 텍스트/숫자 입력 필드
    const inputs = ['name', 'weeks_ahead', 'start_date', 'end_date', 
                   'cooldown_days', 'telegram_bot_token', 'telegram_chat_id'];
    
    // 체크박스 그룹
    const checkboxGroups = ['selected_days', 'selected_types', 'selected_parks'];
    
    // 라디오 버튼 (date_mode)
    // 활성화 체크박스 (is_active)
}
```

### 3. UI/UX 디자인

#### 네오브루탈리즘 스타일
- **카드 디자인**: 두꺼운 테두리, 그림자 효과
- **인터랙션**: 호버 효과, 애니메이션
- **색상 팔레트**: 포레스트 그린 계열
- **타이포그래피**: Outfit (본문), Fraunces (제목)

#### 반응형 디자인
- 모바일 퍼스트 접근
- 그리드 레이아웃: 1열 → 2열 → 3열
- 접근성: ARIA 라벨, 키보드 네비게이션

---

## ⚙️ 설정 옵션 상세

### 1. 날짜 모드

#### 평일 모드 (Weekday Mode)
- **주간 앞**: 모니터링할 주 수 (1-10주)
- **대상 요일**: 금요일(Fri), 토요일(Sat), 일요일(Sun)
- **사용 사례**: 주말 캠핑 예약 모니터링

#### 절대 날짜 모드 (Absolute Date Mode)
- **시작 날짜**: 모니터링 시작일
- **종료 날짜**: 모니터링 종료일
- **사용 사례**: 특정 기간(연휴, 휴가) 예약 모니터링

### 2. 필터 옵션

#### 국립공원 목록 (21개)
```
지리산, 경주, 계룡산, 내장산, 가야산, 덕유산, 오대산, 
주왕산, 태안해안, 다도해해상, 변산반도, 월출산, 소백산, 
월악산, 북한산, 치악산, 한려해상, 속리산, 설악산, 무등산, 태백산
```

#### 시설 유형
- **특화야영장**: 특화된 야영 시설
- **카라반**: 카라반 전용 시설
- **자동차야영장**: 자동차 진입 가능 야영장

### 3. 알림 설정

#### Telegram 통합
- **Bot Token**: Telegram BotFather에서 발급
- **Chat ID**: 개인/그룹 채팅 ID
- **메시지 형식**: 구조화된 예약 정보

#### 쿨다운 시스템
- **목적**: 동일 예약에 대한 스팸 방지
- **기간**: 0-30일 설정 가능
- **기본값**: 1일
- **키 형식**: `YYYYMMDD_ParkName_FacilityType`

---

## 🔄 시스템 워크플로우

### 1. 설정 생성/편집
```
사용자 입력 → 프론트엔드 검증 → API 호출 → DB 저장 → UI 업데이트
```

### 2. 예약 확인 프로세스
```
스케줄러/수동 트리거 → 설정 조회 → KNPS API 호출 → 데이터 파싱 → 필터 적용 → 알림 전송 → 기록 저장
```

### 3. 알림 전송 로직
```
예약 가능성 발견 → 쿨다운 확인 → 메시지 포맷팅 → Telegram 전송 → 성공/실패 로깅
```

---

## 🧪 테스트 및 품질 보증

### 1. 단위 테스트
- `test_db.py`: 데이터베이스 연산 모킹 테스트
- `test_scraper.py`: 날짜 계산 및 API 파싱 로직
- `test_notifier.py`: Telegram 메시지 포맷팅

### 2. 통합 테스트
- `test_integration.py`: Flask 엔드포인트 및 실제 Telegram 알림
- E2E 테스트: Playwright를 통한 전체 워크플로우 검증

### 3. QA 체크리스트
- `QA_CHECKLIST.md`: 핵심 시스템 동작 검증 문서
- 수동 테스트 시나리오
- 에지 케이스 처리

---

## 🚀 배포 및 운영

### 1. 로컬 개발 환경
```bash
# 백엔드 설정
cd backend
pip install -r requirements.txt
python app.py

# 프론트엔드
open frontend/index.html  # 또는 로컬 서버 실행
```

### 2. 데이터베이스 설정
- **로컬**: Supabase CLI + Docker
- **프로덕션**: Supabase 클라우드
- **마이그레이션**: 스키마 동기화 스크립트

### 3. 환경 변수
- `SUPABASE_URL`: 데이터베이스 연결 URL
- `SUPABASE_KEY`: API 키
- 테스트 자격 증명: `config.ini` (git 무시)

---

## 🐛 알려진 문제 및 해결책

### 1. 해결된 문제

#### Edit 폼 인구 문제 (2026-02-24)
- **증상**: 설정 카드 "Edit" 클릭 시 기존 값 로드 실패
- **원인**: 문자열/숫자 비교 버그 (`s.id === settingId`)
- **해결**: 느슨한 비교로 변경 (`s.id == settingId`)
- **위치**: `frontend/index.html` line 601

#### 중복 코드
- **위치**: `populateForm()` 함수
- **문제**: 중복된 `if (!data) return;` 문
- **해결**: 중복 코드 제거

### 2. Windows 특정 문제
- **`nul` 파일 생성**: Windows에서 소문자 `nul`은 파일 생성
- **해결**: 대문자 `NUL` 사용 또는 `.gitignore`에 `nul` 추가

---

## 📈 향후 개선 사항

### 1. 기능 확장
- **다중 사용자 지원**: 사용자별 설정 분리
- **알림 채널 추가**: 이메일, SMS, Discord
- **고급 필터링**: 인원 수, 시설 등급, 가격 범위

### 2. 기술적 개선
- **백그라운드 작업**: Celery/Redis를 통한 비동기 처리
- **모니터링**: 로깅, 메트릭스, 알림
- **캐싱**: Redis 캐시로 API 호출 최적화

### 3. 사용자 경험
- **대시보드 개선**: 실시간 예약 현황 차트
- **모바일 앱**: React Native/iOS/Android 앱
- **다국어 지원**: 영어, 일본어 등

---

## 📚 참조 문서

### 프로젝트 문서
- `AGENTS.md`: 프로젝트 지식 베이스 및 세션 기록
- `QA_CHECKLIST.md`: 품질 보증 체크리스트
- 이 문서: 시스템 전체 문서화

### 외부 리소스
- **KNPS API**: 국립공원공단 예약 시스템
- **Telegram Bot API**: 봇 개발 문서
- **Supabase 문서**: 데이터베이스 및 인증
- **Tailwind CSS**: UI 컴포넌트 스타일링

---

## 👥 유지보수 및 지원

### 코드 컨벤션
- **백엔드**: 모듈화된 서비스, 상태 비저장 로직
- **프론트엔드**: 즉시 백엔드 상태 동기화
- **에러 처리**: 모든 KNPS API 호출 try-except 래핑

### 버전 관리
- **Git 전략**: 기능 브랜치 + PR 검토
- **커밋 규칙**: 의미 있는 커밋 메시지
- **릴리스**: 태그 기반 버전 관리

### 문제 해결
1. **백엔드 실행 확인**: `python app.py` 상태 확인
2. **데이터베이스 연결**: Supabase 연결 테스트
3. **Telegram 자격 증명**: Bot Token 및 Chat ID 유효성 검사
4. **브라우저 콘솔**: 프론트엔드 JavaScript 에러 확인

---

**문서 최종 업데이트**: 2026-02-24  
**시스템 버전**: 1.0.0  
**문서 버전**: 1.0.0