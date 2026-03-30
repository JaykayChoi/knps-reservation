<!-- 이 파일은 사용자 참조용 한국어 번역본입니다 -->
<!-- Claude는 이 파일을 읽지 않습니다. 원본: CLAUDE.md -->

# KNPS 예약 자동 알림 시스템

**핵심 기술 스택:** Python (Flask), Supabase, Tailwind CSS, Telegram Bot API

## 개요
국립공원공단(KNPS) 캠핑장 잔여석을 모니터링하고, 사용자 정의 필터 및 쿨다운 기간에 기반한 실시간 텔레그램 알림을 전송하는 시스템입니다.

## 구조
```
knps-reservation/
├── .claude/              # Claude Code 설정 및 메모리
│   ├── CLAUDE.md         # 프로젝트 지식 베이스 (이 파일)
│   ├── memory/           # 프로젝트 내부 메모리 시스템
│   ├── settings.json     # OMC 플러그인 설정
│   └── skills/           # OMC 스킬
├── backend/              # Python/Flask API 서버 및 핵심 로직
│   ├── app.py            # API 진입점 및 라우터
│   ├── db.py             # Supabase 인터페이스 (설정 및 히스토리)
│   ├── scraper.py        # KNPS API 통신 로직
│   ├── notifier.py       # 텔레그램 알림 서비스
│   ├── requirements.txt  # Python 의존성
│   └── tests/            # pytest 유닛 테스트
├── frontend/             # 웹 기반 설정 대시보드
│   ├── index.html        # Vanilla JS + Tailwind CSS UI (메인 대시보드)
│   └── search.html       # 실시간 잔여석 검색 페이지
├── supabase/             # 데이터베이스 설정 및 마이그레이션
│   ├── config.toml
│   └── migrations/       # SQL 마이그레이션 파일
├── tests/                # E2E 테스트 (Playwright)
│   └── test_dashboard.spec.ts
└── old/                  # 레거시 모놀리식 참고 코드 (읽기 전용)
```

## 어디를 봐야 하나
| 작업 | 위치 | 비고 |
|------|------|------|
| API 라우트 | `backend/app.py` | 설정 동기화 및 수동 체크 트리거 |
| 스크래핑 로직 | `backend/scraper.py` | `selectCampRemainSiteList.do`와 통신 |
| DB 스키마/작업 | `backend/db.py` | Supabase CRUD 및 쿨다운 로직 |
| UI 컴포넌트 | `frontend/index.html` | 설정 폼 및 잔여석 표시 |
| 검색 UI | `frontend/search.html` | 실시간 잔여석 검색 |
| E2E 테스트 | `tests/test_dashboard.spec.ts` | Playwright 브라우저 테스트 |
| DB 마이그레이션 | `supabase/migrations/` | 스키마 변경 이력 |

## 규칙
- **백엔드**: `backend/`에서 모듈식 서비스 사용. 모놀리식 스크립트 금지.
- **데이터베이스**: 모든 영속성은 Supabase를 통해. 핵심 설정에 로컬 스토리지 사용 금지.
- **필터**: 공원명이나 시설 유형 하드코딩 절대 금지. 항상 DB 설정에서 가져올 것.
- **쿨다운**: 알림 스팸 방지를 위해 `cooldown_days` 설정 준수.
- **프론트엔드**: 모던 Tailwind 유틸리티 클래스 사용. "저장" 시 즉시 백엔드와 동기화.
- **에러 처리**: 모든 KNPS API 호출은 try-except로 래핑.
- **전역 상태 금지**: 스크래핑 로직은 무상태로. 설정은 함수에 전달.

## 금지 사항
- 시크릿(토큰, 키) 하드코딩 금지. 환경 변수 사용.
- `old/` 폴더 파일 수정 금지. 참고용만.
- Flask 메인 스레드에서 장시간 스크래핑 실행 금지.

## 명령어
```bash
# 백엔드 설정 및 실행
cd backend
pip install -r requirements.txt
python app.py

# 백엔드 테스트 실행
cd backend && pytest

# E2E 테스트 실행
npx playwright test
```

## 로컬 개발 및 테스트
- **로컬 DB**: Docker를 통한 Supabase CLI (URL: http://127.0.0.1:54321)
- **스키마**: 테이블 `user_settings`, `notification_history`. `start_date`, `end_date` 컬럼으로 사용자 정의 날짜 범위 지원.
- **테스트**: pytest (유닛 테스트), Playwright (E2E).
- **보안**: 로컬 테스트 자격증명은 `config.ini` (git 무시). 절대 커밋 금지.
- **디버그**: 수동 트리거(`POST /api/check`)는 텔레그램 메시지에 `[TEST]` 접두사.

## 참고사항
- KNPS API는 엔드포인트에 따라 `EUC-KR` 또는 `UTF-8` 사용; `scraper.py`에서 인코딩 확인 필요.
- 알림은 `YYYYMMDD_공원명_시설유형`으로 유일성 관리.
- 텔레그램 알림은 메시지 크기 제한을 위해 30개 항목씩 분할.

## Windows 관련 주의사항
- null 장치 리다이렉션에는 대문자 `NUL` 또는 크로스플랫폼 `/dev/null` 사용.
- `nul` 파일은 `.gitignore`에 안전장치로 추가됨.

---

## 사용자 규칙 및 정책

### 메모리 정책
- 세션 시작 시 `.claude/memory/MEMORY.md` 인덱스만 자동 로드
- 개별 메모리 파일은 현재 작업과 관련될 때만 읽기
- 컨텍스트 효율성을 위해 불필요한 문서 로드 금지

### 자동 팀 구성
대규모 작업 요청(코드 구현, 리팩토링, 디버깅, 리뷰 등) 수신 시, 작업 규모와 성격을 평가하여 자동으로 `/oh-my-claudecode:team` 구성.

**기준:**
- **직접 처리**: 간단한 질문, 설정 변경, 메모리 관리, 1개 파일 소규모 편집
- **소규모 팀 (2~3)**: 2~3개 파일 편집, 단일 기능 구현 → 주로 `executor`
- **중규모 팀 (3~5)**: 다수 파일, 새 기능 개발 → `architect` + `executor` + `verifier` 조합
- **대규모 팀 (5+)**: 아키텍처 변경, 대규모 리팩토링 → 역할별 전문 에이전트 풀
- **디버깅**: `debugger` + `tracer` 조합
- **코드 리뷰**: `code-reviewer` + `security-reviewer` 조합

사용자가 명시적으로 팀 구성을 지정하면 그에 따름.

### 메모리 파일 규칙
- 별도의 `feedback` 타입 메모리 파일 생성 금지
- 피드백/규칙은 `CLAUDE.md`에 직접 기록

### Git 규칙
- 사용자가 "깃에 올려줘"라고 하면 **항상 커밋 AND 푸시** (커밋만 하지 않음)
- 이 프로젝트는 **풀 리퀘스트를 사용하지 않으며** **항상 master 브랜치에서 작업**. 피처 브랜치나 PR 생성 금지. master에 직접 커밋 및 푸시.

### Git 정책 - 엄격 시행

**핵심 지시사항**: 이 정책은 반드시 따라야 함. 위반은 심각한 실패.

- **명시적인 사용자 텍스트 요청 없이 git 작업 금지**
- **명시적이란**: 사용자가 "git에 올려줘", "커밋해줘", "푸시해줘" 등을 직접 타이핑해야 함
- **예외 없음**: 문서화든, 버그 수정이든, 완료된 기능이든 상관없음

### MD 파일 작성 규칙
- Claude가 기록 목적으로 작성하는 모든 `.md` 파일은 **영어로 작성**
- 영어 파일 작성 시, 같은 폴더에 **항상 한국어 번역본** `filename.kr.md` 생성
- `.kr.md` 파일은 사용자 참조용; **Claude는 `.kr.md` 파일을 읽지 않음** (읽기 대상에서 제외)
- `.md` 파일을 **수정 또는 생성**할 때, **항상 대응하는 `.kr.md` 파일도 업데이트/생성**
