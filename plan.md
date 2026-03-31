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

## Sprint 7 — 완료 (2026-03-31)
- [x] 텔레그램 봇 v5 (10가지 action, Gemini 100%)
- [x] handleContact/handleVisit/handleSearch/handleStats
- [x] contact_logs 방문 예약 컬럼 추가
- [x] Edge Function npm: import 방식 배포
- [x] 자동 테스트 10/10 통과

---

## Sprint 8 — 진행 중 (CSV 마이그레이션 + 배포 + 실사용)

### Phase 1: 엑셀 마이그레이션 — 완료
- [x] 신한라이프 tool.xlsx → clients 99명 이관
- [x] contact_logs 34건 날짜별 파싱 저장
- [x] 전화번호 정규화 (38건 보정)
- [x] services/contact_log_parser.py 작성

### Phase 2: 버그픽스 (Sprint 8B) — 완료
- [x] BUG-01~08 수정 (db_source, touch_method, OCR, 지도, 팔로업)
- [x] UX-01~05 개선 (유입경로, 필터, 탭 순서, CSV 이동)
- [ ] UX-06: 약관분석 AI 대화창 (P2 — 다음 Sprint)

### Phase 3: Streamlit Cloud 배포 (영민 수동)
- [ ] share.streamlit.io → daecan110@gmail.com-cloud 로그인
- [ ] New app → daecan110-cloud/FCPilot, main, app.py
- [ ] Custom subdomain: fcpilot-kr
- [ ] Secrets: .streamlit/secrets.toml 내용 붙여넣기
- [ ] 스모크 테스트: 5개 탭 로딩 + 보장분석 + 텔레그램 응답 확인

### Phase 4: 실사용 + 피드백 수집
- [ ] 영민: 1~2주 현장 실사용
- [ ] 피드백 수집 → Sprint 9 인풋

---

## 영민 선행 작업 (Phase 3 전)

- [x] 엑셀 데이터 이관 완료
- [ ] Streamlit Cloud 배포 (share.streamlit.io 수동)
- [ ] Daily Reminder cron — Supabase Dashboard → pg_cron + pg_net 활성화

---

## Sprint 9 이후 (백로그)

| 작업 | 비고 |
|------|------|
| UI/UX 개선 | 실사용 피드백 기반 |
| 리마인드 발송 트리거 구현 | Sprint 3 잔여 |
| 텔레그램 봇 분리 (고객관리 vs 개발알림) | 실사용 후 시점 결정 |
| 200줄 초과 파일 리팩토링 | 7개 파일 |
| 보장분석표 하단 셀 병합 검증 | Sprint 1 잔여 |
