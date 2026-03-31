# handoff.md — FCPilot

## 현재 상태
- Phase: **Sprint 5 완료 — 텔레그램 AI 어시스턴트 + QA**
- 마지막 세션: 2026-03-31 (Claude Code)
- Supabase: **ghglnszzjuuvrrwpvhhb** (FCPilot 전용)

## Sprint 1~4 — 완료

## Sprint 5 — 완료

### 완료 내역
- [x] command_queue 테이블 생성
- [x] Supabase Edge Function (telegram-bot, daily-reminder)
- [x] 텔레그램 봇 v4: 100% Gemini + DB 세션 + 동명이인 + 전체삭제
- [x] Gemini 429 대응: 재시도 + 로컬 폴백
- [x] 고객 등록/조회/수정/삭제 전부 동작 확인
- [x] 직전 고객 세션 (DB 저장) 동작 확인
- [x] scripts/command_poller.py (로컬 폴링)
- [x] 텔레그램 webhook 설정 완료
- [x] QA 점검 통과 (API 키/bare except/import 순서)
- [x] 보안 체크리스트 7/7 통과
- [x] Streamlit Cloud 배포 준비 완료

### Streamlit Cloud 배포 (영민 수동)
- [ ] https://share.streamlit.io → New app
- [ ] Repo: japanstudy1205-cloud/FCPilot, Branch: main, File: app.py
- [ ] Custom subdomain: fcpilot-kr
- [ ] Secrets: .streamlit/secrets.toml 내용 붙여넣기
- [ ] Deploy 클릭

### Daily Reminder cron (영민 수동)
- [ ] Supabase Dashboard → Database → Extensions → pg_cron + pg_net 활성화
- [ ] SQL Editor에서 cron.schedule 실행 (handoff.md 이전 버전 참조)

---

## 알려진 이슈
- Gemini 무료 tier: 분당 2회 제한 → 429 시 재시도 + 로컬 폴백 대응
- 200줄 초과 파일 7개: 기존 코드, 향후 Sprint에서 분리
- DB 직접 연결: IPv6 전용 + Pooler 미연결 (connection string 확인 필요)
- Edge Function 세션: bot_sessions 테이블 사용 (인스턴스 간 상태 공유)
