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
- [x] 리마인드 모듈 (구형 — contact_logs 기반)

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

## Sprint 6 — 완료
- [x] pages/ → views/ (Streamlit 사이드바 자동 노출 차단)
- [x] config.toml toolbarMode=minimal, 풋터 CSS 숨김
- [x] users_settings.role 컬럼 (admin/user)
- [x] is_admin() + 설정 탭 admin 전용 섹션
- [x] 보안 점검 ALL CLEAR

## Sprint 7 — 완료
- [x] 텔레그램 봇 v5 (10가지 action, Gemini 100%)
- [x] handleContact/handleVisit/handleSearch/handleStats
- [x] contact_logs 방문 예약 컬럼 추가
- [x] Edge Function npm: import 방식 배포

## Sprint 8 — 완료
- [x] 신한라이프 tool.xlsx → clients 99명 이관
- [x] contact_logs 34건 날짜별 파싱 저장
- [x] BUG-01~08 수정 (db_source, touch_method, OCR, 지도, 팔로업)
- [x] UX-01~05 개선 (유입경로, 필터, 탭 순서)
- [x] fcpilot-kr.streamlit.app 배포

## Sprint 8C Round 3 — 완료
- [x] 간판 OCR 주소 자동입력 — EXIF GPS + Reverse Geocoding + Nominatim 폴백
- [x] 동선기록 이전 기록 조회 개선 — 날짜 선택 + Naver Maps 지도

## 보안 강화 — 완료
- [x] 고객 상세 조회 fc_id 필터 (CRITICAL)
- [x] 삭제 쿼리 전체 fc_id 소유권 검증
- [x] fp_reminders RLS 활성화
- [x] 로그인 에러 메시지 내부 정보 노출 차단

## Sprint 9 — 완료
- [x] fp_products 테이블 + 설정 탭 상품 관리 (CRUD)
- [x] 상담 기록 제안 상품 다중 선택 연동
- [x] fp_reminders 리마인드 시스템 (3구역/등록/수정/완료)
- [x] 고객 상세 리마인드 섹션
- [x] 홈 월간 캘린더 (대기●/완료✓ 배지, 날짜 상세)
- [x] 개척지도/동선기록 Naver Maps JS API v3로 교체
- [x] 홈 최근활동 빠른 버튼 (고객추가/활동추가)
- [x] 통계 기간 6단계
- [x] 상담이력 인라인 수정
- [x] 고객 상세 보장분석 이력 섹션
- [x] 메뉴 "홈" → "오늘의 할일"

## Sprint 10 — 완료 (2026-03-31)
- [x] 매장 수정 + 삭제 (pioneer_shops 팔로업 탭)
- [x] 동선기록 달력 하이라이트 (최근 90일 날짜 요약)
- [x] 보장분석 Excel 영구 저장 (Supabase Storage)
- [x] analysis_records DB 컬럼 버그 수정
- [x] 텔레그램 리마인드 버그 수정 (fp_reminders 미조회, 매장명 누락, 포맷 개선)

---

## 백로그 (우선순위 없음)

| 작업 | 비고 |
|------|------|
| page_clients.py 리팩토링 | ~530줄, 200줄 기준 초과 |
| 텔레그램 봇 분리 | 개발 알림용/사용자용 분리 — 실사용 후 시점 결정 |
| Daily Reminder cron | Supabase Dashboard → pg_cron + pg_net 활성화 필요 |
