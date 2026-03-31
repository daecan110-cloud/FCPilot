# handoff.md — FCPilot

## 현재 상태
- Phase: **Sprint 7 완료 — 텔레그램 봇 v5 NLP 전면 업그레이드**
- 마지막 세션: 2026-03-31 (Claude Code)
- Supabase: **ghglnszzjuuvrrwpvhhb** (FCPilot 전용)

## Sprint 1~6 — 완료

## Sprint 7 — 완료 (2026-03-31)

### 완료 내역
- [x] 텔레그램 봇 v5: 10가지 action (register/query/update/delete/delete_all/contact/visit/search/stats/reminder)
- [x] Gemini NLP 100% — 로컬 폴백 제거
- [x] handleContact: contact_logs 상담 기록
- [x] handleVisit: visit_reserved + visit_datetime
- [x] handleSearch: 등급/지역/기간/키워드 조건 검색
- [x] handleStats: 전체/등급별/상담/개척 통계
- [x] sql/008_contact_logs_visit.sql 실행 완료 (visit_reserved, visit_datetime 컬럼 추가)
- [x] Edge Function 배포: npm:@supabase/supabase-js@2 import (raw source 방식)
- [x] 자동 테스트 10/10 통과 (scripts/test_telegram_bot.py — Edge Function 직접 호출 방식)
- [x] 테스트 결과 텔레그램 보고 완료

### 핵심 발견 사항
- Supabase Management API: `body` 필드에 **raw TypeScript 소스** 전달 (base64 X)
- `npm:@supabase/supabase-js@2` import 사용 (esm.sh X)
- 테스트: getUpdates 불가 (webhook 모드) → Edge Function에 직접 POST로 시뮬레이션

---

## 알려진 이슈
- Gemini 무료 tier: 분당 2회 제한 → 429 시 재시도 대응
- 200줄 초과 파일 7개: 향후 Sprint에서 분리 예정
- Streamlit Cloud 배포 미완료 (영민 수동 작업 필요)

## 영민 수동 작업 대기
- [ ] Streamlit Cloud 배포 — share.streamlit.io (daecan110@gmail.com-cloud)
- [ ] Admin 권한 부여 — Supabase SQL: `UPDATE users_settings SET role = 'admin' WHERE id = '본인_id';`
- [ ] Daily Reminder cron — Supabase Dashboard → pg_cron + pg_net 활성화
