# handoff.md — FCPilot

## 현재 상태
- Phase: **Sprint 17 완료 (디버깅+코드 품질 개선)** — 영민 테스트 대기 중
- 마지막 세션: 2026-04-08 (Claude Code)
- Supabase: **ghglnszzjuuvrrwpvhhb** (FCPilot 전용)
- 배포: **fcpilot-kr.streamlit.app** (git push → 자동 반영)

---

## Sprint 1~9 — 완료 (상세는 git log 참조)

주요 완료 항목 요약:
- 보장분석 + 약관분석 AI (Claude API)
- 고객 CRM (목록/상세/등록/수정/삭제, 전화번호 암호화)
- 상담이력 CRUD (등록/수정/삭제/인라인 수정)
- 개척지도 + OCR (EXIF GPS 자동주소 포함) + 팔로업
- 동선기록 탭 + 카카오맵 JS API 지도 (Sprint 12에서 네이버→카카오 전환)
- 상품 관리 (fp_products) + 상담 제안 상품 연동
- fp_reminders 리마인드 시스템 (3구역 표시/등록/수정/완료)
- 홈 월간 캘린더 (대기●/완료✓ 배지)
- 텔레그램 양방향 봇 (Gemini NLP)
- 쿠키 기반 세션 유지 (새로고침 로그아웃 방지)
- 회원가입 승인 시스템 (pending/approved/rejected)
- 통계 기간 6단계 (오늘/3일/7일/30일/3개월/전체)
- 지오코딩 Nominatim 폴백 (Naver NCP 실패 시 OpenStreetMap)
- 보안 이중 방어 (앱 레이어 fc_id 필터 + DB RLS)

---

## Sprint 10 — 완료 (2026-03-31)

### Round 1
- [x] 매장 수정 + 삭제 (pioneer_shops) — 팔로업 탭에서 수정/삭제 CRUD
- [x] 동선기록 달력 하이라이트 — 이전 기록 탭 최근 90일 방문 날짜 요약 표시

### Round 2
- [x] 보장분석 Excel 영구 저장 — Supabase Storage `analysis-excel` 버킷
- [x] DB 컬럼 버그 수정 (`analysis_result`→`result_summary`, `pdf_filename` 제거)
- [x] 고객 상세 보장분석 이력 → 📥 엑셀 다운로드 버튼
- [x] analysis_records에 `excel_path TEXT` 컬럼 추가 (sql/010)

### 텔레그램 리마인드 버그 수정
- [x] fp_reminders 미조회 버그 — `remind_trigger.py`가 구형 `reminder.py`만 사용하던 문제 수정
- [x] 개척 팔로업 매장명 누락 — `p["shop"]["shop_name"]` 올바르게 참조
- [x] 알림 포맷 개선 — "💬 상담 리마인드" / "🗺️ 개척 팔로업" 섹션 분리

---

## 개발환경 자동화 — 완료 (2026-03-31)

- [x] `.claude/agents/code-reviewer.md` — bare except/API키/개인정보 print/200줄/컬럼명 점검
- [x] `.claude/agents/codebase-explorer.md` — 구조 분석, 호출 관계, 영향 범위 파악
- [x] `.claude/agents/test-runner.md` — 테스트 실행 + 결과 분석
- [x] `CLAUDE.md` 서브에이전트 한국어 별칭 등록 (리뷰/분석/테스트)
- [x] `.claude/settings.json` hooks 설정
  - `SessionStart`: git pull + 보안 스캔 (API키/bare except/데이터파일)
  - `SessionEnd`: 자동 commit + push
  - `PreToolUse`: 민감 파일 수정/읽기 차단, 위험 명령 차단
  - `PostToolUse`: py_compile 구문 검사, 개인정보 print 경고, API키 하드코딩 차단
  - `UserPromptSubmit`: 최근 변경 diff 표시

---

## Sprint 11-1 — 완료 (2026-04-01)

### UI 리뉴얼
- [x] 다크 네이비 사이드바 + 흰색 텍스트
- [x] 메트릭/카드 흰색 배경 + 그림자 + 둥근 모서리(12px)
- [x] Primary 색상 인디고(#4f46e5)로 변경
- [x] Pretendard 폰트 유지

### 홈 UX 개선
- [x] 리마인드 4섹션 → 탭 방식 변경 (오늘/이번주/이번달/미정)
- [x] 캘린더 디자인 개선 + 오늘 버튼 추가
- [x] 리마인드 버튼 on_click 콜백 (더블클릭 문제 해결)

### 버그 수정
- [x] remind_trigger KeyError 'overdue' 수정
- [x] 고객 등급 VIP/S 저장 실패 → DB constraint 확장
- [x] 등급순 정렬 VIP→S→A→B→C→D 순서 수정
- [x] 리마인드 텔레그램 중복 발송 → DB 기반 하루 1회 제한

### 기타
- [x] sprint-done 스킬: 테스트 실패 시 텔레그램 알림 추가
- [x] CLAUDE.md: sprint-done 자동 실행 규칙 추가
- [x] plan.md: 백로그 + Sprint 로드맵 업데이트
- [x] 텔레그램 Claude 챗봇 스크립트 (tools/telegram_chat.py)

---

## 보안 점검 (2026-04-01)

### 수정 완료
- [x] 6개 파일에서 하드코딩 키 제거 (service_role_key, 봇 토큰, DB 비밀번호, FC_ID)
- [x] `utils/secrets_loader.py` 공용 모듈 생성 — CLI 스크립트용 secrets.toml 파서
- [x] hook 보안 스캔 패턴 강화 (JWT/봇토큰/Claude키/Gemini키 실제 포맷 정규식)

### 텔레그램 봇 분리 완료
- [x] `[telegram_dev]` — claudeFC_bot: 작업 알림 (Sprint, 에러, 테스트)
- [x] `[telegram_user]` — FCPilot 봇: 사용자 기능 (고객 조회/등록, 리마인드, Claude 챗)
- [x] Edge Function 환경변수명 변경 (TELEGRAM_USER_BOT_TOKEN)

### 영민 액션 필요
- [x] Supabase service_role 키 재생성
- [x] DB 비밀번호 변경
- [x] BotFather 봇 토큰 2개 재발급
- [x] secrets.toml 전체 업데이트
- [x] exec_sql RPC role 제한 SQL 실행
- [x] **Supabase Edge Function 환경변수** 업데이트 (2026-04-02 완료)
- [x] **Streamlit Cloud secrets** 업데이트 (2026-04-02 완료, telegram_dev/telegram_user 구조)

### 근본 원인
Streamlit 외부 CLI 스크립트에서 `st.secrets`를 못 쓰는 문제를 키 하드코딩으로 우회한 것 (Sprint 5~7 설계 실수)

---

## Sprint 12 — 완료 (2026-04-01)

- [x] 네이버 지도 → 카카오맵 전환 (utils/kakao_map.py + services/geocoding.py)
- [x] 카카오 지오코딩 + 역지오코딩 연동
- [x] page_clients.py 560줄 → 3파일 분리 (263+175+126)
- [x] 미사용 create_route_map 호출 제거

---

## Sprint 13 — 완료 (2026-04-02)

### 기타 이슈 수정
- [x] 캘린더 중복 렌더링 수정 — HTML 캘린더 제거, st.button 통일 + 뱃지 표시
- [x] 구형 `services/reminder.py` 삭제 — 미사용 확인, fp_reminders로 대체됨

### 테스트 수정
- [x] `services.reminder` → `services.fp_reminder_service` 변경
- [x] `fp_` 접두사 검사 allowlist 추가 (DB 테이블명/쿠키명 오탐 해소)
- [x] 테스트 결과 텔레그램 발송 제거

### 파일 분리 (전 파일 200줄 이하)
- [x] `page_analysis.py` (343줄) → `page_analysis.py` (158) + `page_analysis_yakwan.py` (186)
- [x] `page_home.py` (294줄) → `page_home.py` (145) + `page_home_forms.py` (155)
- [x] `page_pioneer_map.py` (350줄) → `page_pioneer_map.py` (116) + `page_pioneer_followup.py` (134) + `page_pioneer_ocr.py` (118)
- [x] `page_pioneer_route.py` (239줄) → `page_pioneer_route.py` (120) + `page_pioneer_history.py` (120)

### 버그 수정
- [x] `page_pioneer_route.py:200` 미사용 `create_route_map()` 호출 제거

### 코드 품질 개선
- [x] 에러 메시지 보안 — `page_settings.py`, `page_settings_admin.py` safe_error 적용
- [x] `page_clients.py` 고객 저장 시 로딩 표시 추가
- [x] `page_home_forms.py` 활동 추가 시 로딩 표시 추가
- [x] AI 응답 실패 시 safe_error 사용으로 변경

---

## Sprint 14 — 완료 (2026-04-04)

- [x] 동료 FC 온보딩 확인 — 기존 Sprint에서 구현 완료 확인 (회원가입 승인, Admin UI, 텔레그램 알림)
- [x] 텔레그램 봇 분리 (#15) 확인 — dev/user 분리 완료 확인
- [x] RLS + fc_id 보안 전 테이블 확인

---

## Sprint 15 — 완료 (2026-04-07)

### 지도 전환
- [x] 카카오맵 JS SDK → folium+streamlit-folium 전환 (Streamlit iframe sandbox 호환)
- [x] 개척지도/동선기록/이전기록 모두 folium 기반으로 통합
- [x] st_folium 중복 key 에러 수정

### 간판 OCR 개선
- [x] 카카오 장소 검색 연동 — 매장명으로 검색 → 주소/좌표 자동 입력
- [x] OCR 프롬프트 강화 — 작은 글씨(주소/전화번호) 추출율 개선
- [x] 비유효 주소 자동 필터 (한국 주소 패턴 체크)
- [x] OCR 등록 후 화면 리셋 + 성공 메시지

### 간판 사진 저장
- [x] Supabase Storage `pioneer-photos` 버킷 생성 (public)
- [x] OCR 등록 시 사진 업로드 → photo_url DB 저장
- [x] 팔로업 현황에서 간판 사진 표시

### 팔로업 강화
- [x] 전체 삭제 기능 (2단계 확인)

### 기타
- [x] Streamlit 정적 파일 서빙 활성화 (config.toml)
- [x] components.html 지원 중단 대응 (st.iframe 전환)
- [x] geocoding.py 에러 메시지 표시 추가

---

## Sprint 16 — 완료 (2026-04-08)

### 유입경로 디버깅
- [x] `config.py`에 `DEFAULT_SOURCE_CATEGORIES` 단일 소스 정의 ("지인"으로 통일)
- [x] `page_clients.py`, `page_settings.py` 양쪽 중복 제거 → config import
- [x] `sql/015_normalize_db_source.sql` — 기존 "개인(지인)" 데이터 정규화

### 기계약자 계약 정보 관리
- [x] `sql/016_client_contracts.sql` — client_contracts 테이블 (RLS 적용)
- [x] `views/page_clients_contracts.py` — 계약 정보 CRUD UI
- [x] `page_clients_detail.py` — S/VIP일 때만 "계약정보" 탭 노출
- [x] 직접 입력 + 상품설계서 PDF 업로드 지원

### 상품설계서 PDF 파싱
- [x] `services/contract_extractor.py` — pdfplumber 텍스트 추출 + Claude API 구조화
- [x] 주계약/특약/보험료/보험사/카테고리 자동 추출

### 상품 판매 통계
- [x] `page_stats.py` — "상품 판매 현황" 섹션 추가
- [x] 판매 랭킹, 제안 vs 실제 판매, 나이대별 상품, 가격대별 분포

### 영민 액션 필요
- [ ] `sql/015_normalize_db_source.sql` Supabase SQL Editor 실행
- [ ] `sql/016_client_contracts.sql` Supabase SQL Editor 실행

---

## Sprint 17 — 완료 (2026-04-08)

### 버그 수정
- [x] BUG-1: 홈 → 고객관리 네비게이션 실패 (`_nav_to "고객관리"` → `"👥 고객관리"`)
- [x] BUG-2: 고객 삭제 시 fp_reminders/client_contracts 미삭제 (고아 데이터)

### 200줄 초과 파일 분리 (4건)
- [x] `page_stats.py` 434→244줄 + `page_stats_products.py` 190줄
- [x] `pdf_extractor.py` 400→221줄 + `pdf_extractor_detail.py` 167줄
- [x] `telegram.py` 279→141줄 + `telegram_commands.py` 143줄
- [x] `page_clients.py` 264→181줄 + `page_clients_form.py` 92줄

### 코드 품질
- [x] `contract_extractor.py`: 미사용 import base64 제거 + get_secret→load_secrets 수정
- [x] `config.toml`: `ark[theme]` → `[theme]` 오타 수정
- [x] `test_all.py`: 17개 모듈 추가 (56/56 통과)

### 보안 체크
- [x] 8항목 전체 통과 (API키/고객데이터/print/bare except/HTML이스케이프/HTTP/gitignore/fc_id)

---

## 미완료 항목

| 우선순위 | 항목 | 비고 |
|----------|------|------|
| 🟢 LOW | tools/telegram_chat.py | 별도 봇 토큰 설정 완료, 필요 시 사용 |
| 🟡 MED | 매장 등록 탭 카카오 검색 | 구현됨, 테스트 필요 |

---

## DB 스키마 변경 이력 (Sprint 9 이후)

| 테이블 | 변경 | 용도 |
|--------|------|------|
| fp_products | 신규 생성 + RLS | 상품 관리 |
| fp_reminders | 신규 생성 + RLS | 리마인드 (홈/고객상세) |
| users_settings | status TEXT 추가 | 회원가입 승인 |
| contact_logs | proposed_product_ids uuid[] 추가 | 제안 상품 연동 |
| analysis_records | excel_path TEXT 추가 | Excel 파일 Storage 경로 |
| client_contracts | 신규 생성 + RLS | 기계약자 계약 정보 (S/VIP) |

## Supabase Storage

| 버킷 | 공개 여부 | 용도 |
|------|----------|------|
| analysis-excel | private | 보장분석 Excel 결과물 ({fc_id}/{record_id}.xlsx) |
| pioneer-photos | public | 간판 사진 ({fc_id}/{uuid}.jpeg) |

---

## 알려진 이슈

- Gemini 무료 tier: 분당 2회 제한 → 429 시 자동 재시도 대응 완료
- Streamlit Cloud `st.html()` height 파라미터 미지원 — folium으로 우회

---

## 다음 세션 시작 시

1. `git pull origin main`
2. 실사용 피드백 수집 및 버그 수집
