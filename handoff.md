# handoff.md — FCPilot

## 현재 상태
- Phase: **Sprint 8B 완료 — 버그픽스 + 마이그레이션**
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

## Sprint 8 완료 내역

### Phase 1: 엑셀 마이그레이션 — 완료
- [x] `신한라이프 tool의 사본.xlsx` → clients 99명 + contact_logs 34건 이관
- [x] `scripts/migrate_excel.py` 작성 (dry-run/run 모드)
- [x] `services/contact_log_parser.py` — 날짜별 상담 내용 파싱
- [x] 전화번호 float→int 정규화 (38건 DB 직접 보정)
- [x] FC_ID: `ee41ae34-feef-4689-b005-f144cab4e4a6` (김영민fc)

### Phase 2: Sprint 8B 버그픽스 — 완료 (commit: 56bd463)
- [x] BUG-01: `source` → `db_source` 컬럼명 수정
- [x] BUG-02: `contact_type`/`content` → `touch_method`/`memo`
- [x] BUG-04: 전화번호 표시 형식 수정
- [x] BUG-05: OCR 프롬프트 개선 + 업종 드롭다운
- [x] BUG-06: EXIF GPS → Naver Reverse Geocoding 주소 자동 추출
- [x] BUG-07: 매장 클릭 → 지도 center 이동 (session_state 기반)
- [x] BUG-08: `fp_pioneer_shops` → `pioneer_shops` 조인 수정 + 팔로업 개선
- [x] UX-01: 출처 → 유입경로 라벨
- [x] UX-02: 고객 목록 필터 (나이대/지역/상담유무/정렬)
- [x] UX-04: 영업 모드별 탭 순서 변경
- [x] UX-05: CSV 가져오기 → 설정 탭으로 이동

### 미완료 (P2 — 다음 Sprint)
- [ ] UX-06: 약관분석 AI 대화창 (page_analysis.py)
- [ ] BUG-03: 뒤로가기 로그아웃 (Streamlit 제한 — 해결 어려움)

## 알려진 이슈
- Gemini 무료 tier: 분당 2회 제한 → 429 시 재시도 대응
- 200줄 초과 파일 7개: 향후 Sprint에서 분리 예정

## 배포 상태
- **fcpilot-kr.streamlit.app** — 자동 배포 (git push → 자동 반영)
- main 브랜치 push 시 Streamlit Cloud가 자동 재빌드

## 다음 Sprint
1. fcpilot-kr.streamlit.app 접속 → 최신 변경사항 스모크 테스트
2. 실사용 + 피드백 수집 (1~2주)
3. UX-06 약관분석 AI 대화창
