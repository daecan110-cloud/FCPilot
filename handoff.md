# handoff.md — FCPilot

## 현재 상태
- Phase: **보안 Sprint 완료 — 영민 테스트 대기 중**
- 마지막 세션: 2026-04-01 (Claude Code)
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
- [ ] **Supabase Edge Function 환경변수** 업데이트 (미완료)
  - `TELEGRAM_USER_BOT_TOKEN` = FCPilot 봇 토큰
  - `TELEGRAM_USER_CHAT_ID` = 8201988543
  - 기존 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 삭제
- [ ] **Streamlit Cloud secrets** 업데이트 (telegram → telegram_dev/telegram_user 구조 변경)

### 근본 원인
Streamlit 외부 CLI 스크립트에서 `st.secrets`를 못 쓰는 문제를 키 하드코딩으로 우회한 것 (Sprint 5~7 설계 실수)

---

## 미완료 항목

| 우선순위 | 항목 | 비고 |
|----------|------|------|
| 🟡 MID | 캘린더 날짜 버튼이 HTML과 중복 렌더링 | HTML 캘린더 + st.button 그리드 겹침 가능성 |
| 🟢 LOW | 200줄 초과 파일 리팩토링 | page_clients.py (~530줄) |
| ✅ DONE | 텔레그램 봇 분리 | dev(claudeFC_bot) / user(FCPilot) 완료 |
| 🟢 LOW | tools/telegram_chat.py | 별도 봇 토큰 설정 완료, 필요 시 사용 |

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
