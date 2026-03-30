---
name: 세션 히스토리
description: 과거 세션 성과 및 주요 결정사항
type: project
---

## 세션 히스토리 (AGENTS.md에서 마이그레이션, 2026-02-23 ~ 2026-02-26)

### 2026-02-23
- 버그 수정: Supabase user_settings 테이블에 누락된 start_date/end_date 컬럼 추가로 500 에러 해결
- 테스트 스위트: 모든 모듈에 걸쳐 20개 이상 자동화 테스트 구현 (pytest + mocker)
- DevOps: 로컬 Docker 기반 DB 개발을 위한 Supabase CLI 통합
- UI/UX: 네오브루탈리스트 대시보드 개선, "전체 선택", 수동 테스트 트리거
- 보안: 테스트 자격증명용 config.ini, .gitignore 업데이트
- QA: QA_CHECKLIST.md 생성, Playwright E2E 자동화

### 2026-02-24
- 버그 수정: 편집 폼 데이터 로딩 - 문자열 vs 숫자 비교 (=== → ==)
- DB 최적화: system_status 스키마 간소화, last_check_time → last_check_at 이름 변경
- 자동 유지보수: 알림 히스토리 정리 (7일 보관), 마지막 체크 시간 추적
- 스키마 변경 후 34개 전체 테스트 통과

### 2026-02-26
- 신규 기능: scraper.py에 대기열 알림 추가
- 알림 최적화: 텔레그램 메시지 청킹 (30개 항목/메시지)
- 설정별 히스토리: 사용자 설정별 세분화된 쿨다운
- DB 리팩토링: notification_history에서 중복 식별자 컬럼 제거
- 신규 기능: "모든 히스토리 삭제" 버튼, DELETE /api/history 엔드포인트
- 빠른 검색: 별도 페이지(search.html)에서 실시간 잔여석 검색
- UI 정리: 대시보드 간소화, LINE#ID 아티팩트 제거

### 2026-03-30
- 마이그레이션: opencode (AGENTS.md)에서 Claude Code (.claude/CLAUDE.md)로 전환
- 메모리: .claude/memory/에 프로젝트 내부 메모리 시스템 구축
