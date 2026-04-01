# handoff.md — FCPilot

## 현재 상태
- Phase: **Sprint 10 완료 + 개발환경 자동화 (서브에이전트 + Hooks)**
- 마지막 세션: 2026-03-31 (Claude Code)
- Supabase: **ghglnszzjuuvrrwpvhhb** (FCPilot 전용)
- 배포: **fcpilot-kr.streamlit.app** (git push → 자동 반영)

---

## Sprint 1~9 — 완료 (상세는 git log 참조)

주요 완료 항목 요약:
- 보장분석 + 약관분석 AI (Claude API)
- 고객 CRM (목록/상세/등록/수정/삭제, 전화번호 암호화)
- 상담이력 CRUD (등록/수정/삭제/인라인 수정)
- 개척지도 + OCR (EXIF GPS 자동주소 포함) + 팔로업
- 동선기록 탭 + Naver Maps JS API v3 지도
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

## 미완료 항목

| 우선순위 | 항목 | 비고 |
|----------|------|------|
| 🟢 LOW | 200줄 초과 파일 리팩토링 | page_clients.py (~530줄) |
| 🟢 LOW | 텔레그램 봇 분리 | 개발 알림용/사용자용 분리 (실사용 후 결정) |

---

## DB 스키마 변경 이력 (Sprint 9 이후)

| 테이블 | 변경 | 용도 |
|--------|------|------|
| fp_products | 신규 생성 + RLS | 상품 관리 |
| fp_reminders | 신규 생성 + RLS | 리마인드 (홈/고객상세) |
| users_settings | status TEXT 추가 | 회원가입 승인 |
| contact_logs | proposed_product_ids uuid[] 추가 | 제안 상품 연동 |
| analysis_records | excel_path TEXT 추가 | Excel 파일 Storage 경로 |

## Supabase Storage

| 버킷 | 공개 여부 | 용도 |
|------|----------|------|
| analysis-excel | private | 보장분석 Excel 결과물 ({fc_id}/{record_id}.xlsx) |

---

## 알려진 이슈

- Naver Maps JS API: NCP 콘솔에서 `fcpilot-kr.streamlit.app` 도메인 등록 필요
- Gemini 무료 tier: 분당 2회 제한 → 429 시 자동 재시도 대응 완료
- page_clients.py ~530줄 (200줄 초과) — 향후 분리 예정
- `reminder.py` (구형 contact_logs 기반 리마인드 조회)는 fp_reminders와 별개로 존재 — 사용처 없으면 추후 정리 필요

---

## 다음 세션 시작 시

1. `git pull origin main`
2. 실사용 피드백 수집 및 버그 수집
