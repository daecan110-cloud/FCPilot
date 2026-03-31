# plan.md — FCPilot

---

## Sprint 1 — 완료
- [x] 프로젝트 초기화, Supabase 테이블, Auth
- [x] 보장분석 탭 (PDF → 엑셀)
- [x] 텔레그램 알림 모듈
- [x] 약관 분석 AI 대화창
- [x] 세액공제 셀 병합 수정

## Sprint 2 — 완료
- [x] 고객 목록/상세/등록/수정 UI
- [x] 상담 이력 기록
- [x] 간판 OCR (Claude Vision)
- [x] 개척지도 탭 (folium)
- [x] Naver Maps Geocoding

## Sprint 3 — 완료
- [x] 약관분석 K열 반영
- [x] 동선 추적 탭
- [x] 팔로업 상태머신
- [x] 리마인드 모듈

## Sprint 4 — 완료
- [x] 텔레그램 양방향
- [x] 홈/통계 대시보드
- [x] Supabase 신규 프로젝트 마이그레이션 (fp_ 접두사 제거)

## Sprint 5 — 완료
- [x] command_queue 테이블
- [x] Supabase Edge Function (telegram-bot, daily-reminder)
- [x] 텔레그램 봇 v4 (Gemini NLP + DB 세션 + 동명이인)
- [x] scripts/command_poller.py
- [x] 텔레그램 webhook 설정

## Sprint 6 — 완료 (2026-03-31)
- [x] pages/ → views/ (Streamlit 사이드바 자동 노출 차단)
- [x] config.toml toolbarMode=minimal, 풋터 CSS 숨김
- [x] users_settings.role 컬럼 (admin/user)
- [x] is_admin() + 설정 탭 admin 전용 섹션
- [x] 보안 점검 ALL CLEAR
- [x] CLAUDE.md / plan.md / tests/test_all.py 정합성 수정

---

## 수동 작업 대기 (영민)

- [ ] Streamlit Cloud 배포 — share.streamlit.io (daecan110@gmail.com-cloud)
- [ ] Admin 권한 부여 — Supabase SQL: `UPDATE users_settings SET role = 'admin' WHERE id = '본인_id';`
- [ ] Daily Reminder cron — Supabase Dashboard → pg_cron + pg_net 활성화

---

## Sprint 7 — 완료 (2026-03-31)
- [x] 텔레그램 봇 v5 (10가지 action, Gemini 100%)
- [x] handleContact/handleVisit/handleSearch/handleStats
- [x] contact_logs 방문 예약 컬럼 추가
- [x] Edge Function npm: import 방식 배포
- [x] 자동 테스트 10/10 통과

---

## 다음 Sprint 후보

| 항목 | 우선순위 |
|------|---------|
| 200줄 초과 파일 분리 (excel_generator 512줄 등 6개) | 높음 |
| Streamlit Cloud 배포 후 실사용 테스트 | 높음 |
| 텔레그램 봇 분리 (개발 알림용 / FCPilot 사용자용) | 중간 |
