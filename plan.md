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

## 개발환경 자동화 — 완료 (2026-03-31)
- [x] `.claude/agents/` 서브에이전트 3개 (code-reviewer, codebase-explorer, test-runner)
- [x] CLAUDE.md 한국어 별칭 등록
- [x] `.claude/settings.json` hooks (SessionStart/End, PreToolUse, PostToolUse, UserPromptSubmit)

## Sprint 11-1 — 완료 (2026-04-01)
- [x] UI 리뉴얼 (다크 사이드바, 인디고 테마, 카드 그림자)
- [x] 홈 리마인드 탭 방식 변경 + 캘린더 디자인 개선 + 오늘 버튼
- [x] 리마인드 버튼 더블클릭 문제 해결 (on_click 콜백)
- [x] 고객 VIP/S 등급 저장 실패 수정 (DB constraint 확장)
- [x] 등급순 정렬 VIP→S→A→B→C→D 수정
- [x] 리마인드 텔레그램 중복 발송 수정 (DB 기반 하루 1회)
- [x] remind_trigger KeyError 'overdue' 수정

## 보안 Sprint — 완료 (2026-04-01)
- [x] API 키/토큰/비밀번호 하드코딩 제거 (6파일) + secrets_loader 공용 모듈
- [x] 전 API 키 재발급 (Supabase, Claude, Telegram x2, Gemini, DB PW)
- [x] 텔레그램 봇 분리 — dev(claudeFC_bot) / user(FCPilot)
- [x] command_poller 명령어 인젝션 차단 (shell=False + 화이트리스트)
- [x] XSS 이스케이프 7건 (esc(), _e(), _safe_json, grade_badge)
- [x] fc_id 누락 쿼리 9건 보강
- [x] 에러 메시지 DB 스키마 노출 차단 38건 (safe_error)
- [x] exec_sql RPC anon 차단
- [x] 파일 업로드 magic bytes 검증
- [x] Hook 자동 차단 6종 + CLAUDE.md 보안 규칙 6조

---

## 백로그 — 미처리 항목 (기존 Sprint에서 이월)

| # | 항목 | 출처 | 상태 |
|---|------|------|------|
| 15 | 텔레그램 봇 분리 (고객관리 vs 개발알림) | MASTER 백로그 | ✅ 완료 |
| 16 | 약관분석 AI 대화창 (Gemini 무료 한계로 보류) | Sprint 8C | 보류 |
| 17 | 200줄 초과 파일 리팩토링 | Sprint 6 이슈 | ✅ 완료 |
| 18 | 보장분석표 하단 셀 병합 검증 | Sprint 1 잔여 | 미착수 |
| 19 | Daily Reminder 자동 발송 (pg_cron + 매일 아침 9시) | Sprint 5 | 미착수 |
| 20 | CSV 내보내기 (백업 기능) | Sprint 8C UX-05 | 미착수 |

## 백로그 — 신규 제안

| # | 항목 | 이유 |
|---|------|------|
| 21 | 고객 생일/기념일 알림 | FC 영업 터치 포인트 핵심. 생년월일 필드 추가 → 리마인드 자동 생성 |
| 22 | 보장분석 비교 (이전 vs 현재) | 같은 고객 재분석 시 변경점 한눈에 — 갱신형 점검에 유용 |
| 23 | 개척 동선 최적화 (방문 순서 추천) | 매장 좌표 기반 최단 경로 제안 — 카카오맵 Directions API 활용 |
| 24 | 모바일 PWA 설정 | Streamlit 앱을 홈 화면에 추가 — 외근 시 앱처럼 사용 |
| 25 | 고객 데이터 자동 백업 (주 1회) | Supabase → CSV 자동 내보내기. 데이터 유실 방지 |
| 26 | 상담 스크립트/멘트 템플릿 | 상황별 첫 멘트 추천 (초회/재상담/거절 후 재접근 등). 설정에서 커스텀 |

## Sprint 14 — 완료 (2026-04-04)
- [x] 동료 FC 온보딩 — 회원가입 승인 시스템 (pending/approved/rejected) + Admin UI
- [x] 텔레그램 봇 분리 (#15) — dev(claudeFC_bot) / user(FCPilot) 완전 분리
- [x] RLS + fc_id 필터링 전 테이블 적용 확인

## Sprint 15 — 완료 (2026-04-07)
- [x] 카카오맵 JS SDK → folium+streamlit-folium 전환
- [x] 간판 OCR 카카오 장소 검색 연동 (주소/좌표 자동 입력)
- [x] 간판 사진 Supabase Storage 저장 + 팔로업에서 표시
- [x] 팔로업 전체 삭제 기능
- [x] OCR 프롬프트 강화 + 비유효 주소 필터
- [x] st_folium 중복 key 수정 + components.html 지원 중단 대응

## Sprint 16 — 완료 (2026-04-08)
- [x] 유입경로 중복 디버깅 — "개인(지인)"→"지인" 통일, 기본값 config.py 단일 소스
- [x] client_contracts 테이블 + 계약 정보 UI (S/VIP 전용 탭)
- [x] 상품설계서 PDF 파싱 (Claude API 기반 주계약/특약 자동 추출)
- [x] 상품 판매 통계 대시보드 (판매 랭킹/제안vs실제/나이대별/가격대별)

## Sprint 17 — 완료 (2026-04-08)
- [x] BUG-1: 홈→고객관리 네비게이션 실패 수정
- [x] BUG-2: 고객 삭제 시 고아 데이터 수정 (fp_reminders/client_contracts)
- [x] 200줄 초과 파일 4건 분리 (page_stats/pdf_extractor/telegram/page_clients)
- [x] contract_extractor import 버그 수정 + config.toml 오타 수정
- [x] test_all.py 17개 모듈 추가 (56/56 통과)
- [x] 보안 체크 8항목 전체 통과

## Sprint 18 — 완료 (2026-04-16)
- [x] 보장분석표 리뷰 섹션 서식 복구 (_fill_review_all 병합 재생성)
- [x] 상급종합병원 암주요치료비 파싱 수정 (Row 30-33 단일/복수 entry 처리)
- [x] 특정순환계질환 주요치료비특약 파싱 수정 (Row 49-53 순차 분배)
- [x] 상세페이지 truncated 텍스트 대응 키워드 추가
- [x] 테스트 50/56 통과 (folium/telegram 6건은 기존 이슈)

## Sprint 19 — 완료 (2026-04-20)
- [x] 보안 전면 점검 — brute force 차단, fail-closed, exec_sql 권한 차단, Storage 경로 검증
- [x] 비밀번호 찾기(재설정) 기능 추가
- [x] 보안 미들웨어 utils/security.py 신규 (입력 검증 + 경로 검증)
- [x] DB 에러 노출 5건 + XSS 1건 수정
- [x] 데드 파일 2개 삭제 + 데드코드 15건 제거
- [x] 중복 상수 3종 config.py 통합 (TOUCH_OPTIONS, CATEGORY_OPTIONS, INSURANCE_*)
- [x] excel_generator.py 724줄 → 365줄 리팩터링 (excel_helpers.py + excel_review.py 분리)
- [x] O(N²) → O(N) 최적화 + contact_logs 쿼리 범위 한정
- [x] RLS 12/12 + exec_sql 권한 차단 → 보안 등급 A
- [x] 테스트 51/55 통과 (4건 기존 환경 문제)

## Sprint 로드맵

| Sprint | 내용 | 크기 |
|--------|------|------|
| 11 | UI 리뉴얼 + 잔여 버그 + 텔레그램 버그 | ✅ 완료 |
| 12 | 보안 전면 점검 + 카카오맵 전환 + 리팩토링 | ✅ 완료 |
| 13 | 실사용 테스트 + 피드백 + UX 개선 | ✅ 완료 |
| 14 | 동료 FC 온보딩 + 봇 분리(#15) | ✅ 완료 |
| 15 | 지도 전환 + OCR 개선 + 팔로업 강화 | ✅ 완료 |
| 16 | 기계약자 계약관리 + 상품 판매 통계 + 유입경로 디버깅 | ✅ 완료 |
| 17 | 디버깅 + 코드 품질 개선 (파일 분리 4건 + 버그 2건) | ✅ 완료 |
| 18 | 보장분석 파싱/서식 디버깅 (암주요치/특정순환계 + 병합 복구) | ✅ 완료 |
| 19 | 보안 강화 + 코드 품질 전면 점검 + 리팩터링 | ✅ 완료 |
| 20 | 생일알림(#21) + Daily Reminder(#19) + 자동백업(#25) | 3~4일 |
| 21 | 보장분석 비교(#22) + 셀 병합 검증(#18) | 3~4일 |
| 22 | 상담 스크립트(#26) + 약관 AI 대화창(#16, API 여유 시) + PWA(#24) | 1주 |
