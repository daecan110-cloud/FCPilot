# handoff.md — FCPilot

## 현재 상태
- Phase: **Sprint 9 Round 3 완료 + 보안강화 + UI개선**
- 마지막 세션: 2026-03-31 (Claude Code)
- Supabase: **ghglnszzjuuvrrwpvhhb** (FCPilot 전용)
- 배포: **fcpilot-kr.streamlit.app** (git push → 자동 반영)

---

## Sprint 1~8C Round 2 — 완료 (상세는 git log 참조)

주요 완료 항목 요약:
- 보장분석 + 약관분석 AI (Claude API)
- 고객 CRM (목록/상세/등록/수정/삭제, 전화번호 암호화)
- 상담이력 CRUD (등록/수정/삭제)
- 개척지도 + OCR + 팔로업
- 동선기록 탭
- 텔레그램 양방향 봇 (Gemini NLP)
- 쿠키 기반 세션 유지 (새로고침 로그아웃 방지)
- 회원가입 승인 시스템 (pending/approved/rejected)
- 영업 모드별 탭 순서 변경
- 유입경로 드래그앤드롭 커스터마이징

---

## Sprint 8C Round 3 — 부분 완료

- [x] 간판 OCR 주소 자동입력 — EXIF GPS + Reverse Geocoding + Nominatim 폴백
- [x] 동선기록 이전 기록 조회 개선 — 날짜 선택 + Naver Maps 지도
- [ ] **매장 수정 + 삭제** (pioneer_shops) — 미완료
- [ ] **동선기록 달력 하이라이트** — 방문 기록 있는 날 달력에 표시 — 미완료

---

## Sprint 9 Round 1 (상품 관리) — 완료

- [x] fp_products 테이블 생성 + RLS
- [x] 설정 탭 상품 관리 섹션 (이름+카테고리, data_editor, 카테고리별 색상 아이콘)
- [x] 상담 기록에 제안 상품 다중 선택 (contact_logs.proposed_product_ids)
- [x] 상품 CRUD (등록/수정/삭제/활성화 토글)

---

## Sprint 9 Round 2 (상담 리마인드) — 완료

- [x] fp_reminders 테이블 생성 + RLS 정책 (sql/009)
- [x] 홈 탭 리마인드 3구역 표시 (지연🔴/오늘🟡/이번주🔵)
- [x] 홈 탭 리마인드 추가 (고객 검색 → 날짜/목적/상품/메모)
- [x] 홈 탭 리마인드 인라인 수정 + 완료 처리
- [x] 고객 상세 → 리마인드 섹션 (등록/완료/취소)

---

## Sprint 9 Round 3 (캘린더 + 기능 개선) — 완료

- [x] 홈 탭 월간 캘린더 (대기●/완료✓ 배지, 월 이동, 날짜 클릭 상세)
- [x] 개척지도/동선기록 Naver Maps JS API v3로 교체
- [x] 지오코딩 Nominatim 폴백 (Naver NCP 실패 시 OpenStreetMap)
- [x] 동선 좌표 없는 매장 경고 + 일괄 재조회 버튼
- [x] 홈 최근활동 — 👤고객추가 / 📝활동추가 빠른 버튼
- [x] 통계 기간 6단계 (오늘/3일/7일/30일/3개월/전체)
- [x] 상담이력 인라인 수정 (수정/저장/취소)
- [x] 고객 상세 보장분석 이력 섹션
- [x] 메뉴 "홈" → "오늘의 할일"

---

## 보안 강화 — 완료 (commit: 63463e3)

- [x] 고객 상세 조회에 fc_id 필터 추가 (CRITICAL 수정)
- [x] 삭제 쿼리 전체 fc_id 소유권 검증
- [x] 리마인드 완료/취소/수정 fc_id 파라미터 추가
- [x] fp_reminders RLS 활성화 (sql/009 DB 적용 완료)
- [x] 로그인 에러 메시지 내부 정보 노출 차단
- 방어 구조: **앱 레이어 fc_id 필터 + DB RLS 이중 방어**

---

## 미완료 항목 (다음 세션 우선순위)

| 우선순위 | 항목 | 비고 |
|----------|------|------|
| 🔴 HIGH | 매장 수정 + 삭제 (pioneer_shops) | Sprint 8C Round 3 잔여 |
| 🟡 MED | 동선기록 달력 하이라이트 | 방문 기록 있는 날 강조 |
| 🟡 MED | 보장분석 Excel/PDF 영구 저장 | Supabase Storage 연동 필요 |
| 🟢 LOW | 200줄 초과 파일 리팩토링 | page_clients.py 등 |

---

## DB 스키마 변경 이력 (Sprint 9 이후)

| 테이블 | 변경 | 용도 |
|--------|------|------|
| fp_products | 신규 생성 | 상품 관리 |
| fp_reminders | 신규 생성 + RLS | 리마인드 |
| users_settings | status TEXT 추가 | 회원가입 승인 |
| contact_logs | proposed_product_ids uuid[] 추가 | 제안 상품 연동 |

## 알려진 이슈

- Naver Maps JS API: NCP 콘솔에서 `fcpilot-kr.streamlit.app` 도메인 등록 필요
- Gemini 무료 tier: 분당 2회 제한 → 429 시 자동 재시도 대응 완료
- page_clients.py 530줄 (200줄 초과) — 향후 분리 예정

## 다음 세션 시작 시

1. `git pull origin main`
2. **매장 수정/삭제 구현** (pioneer_shops) — 최우선
3. 실사용 피드백 수집 병행
