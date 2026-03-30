---
name: KNPS 예약 프로젝트 개요
description: 핵심 프로젝트 컨텍스트 - Flask/Supabase/Telegram 캠핑장 모니터링 시스템
type: project
---

KNPS 예약 자동 알림 시스템은 국립공원공단 캠핑장 잔여석을 모니터링하고 실시간 텔레그램 알림을 전송합니다.

**기술 스택:** Python Flask 백엔드, Supabase (PostgreSQL), Vanilla JS + Tailwind CSS 프론트엔드, Telegram Bot API, Playwright E2E 테스트, pytest 유닛 테스트.

**핵심 아키텍처:**
- 백엔드 모듈: app.py (라우트), db.py (Supabase CRUD), scraper.py (KNPS API), notifier.py (텔레그램)
- 프론트엔드: index.html (대시보드), search.html (실시간 검색)
- 데이터베이스: Supabase, 5개 마이그레이션, 테이블: user_settings, notification_history, system_status
- 배포: Render (되돌림), 로컬 개발은 Supabase CLI + Docker

**목적:** 사용자 맞춤 필터, 날짜 범위, 알림 쿨다운으로 KNPS 캠핑장 잔여석 모니터링.
**적용 방법:** 모든 백엔드 작업은 모듈식 서비스로, 모놀리식 스크립트 금지. 필터는 DB에서 가져오며 하드코딩 금지.
