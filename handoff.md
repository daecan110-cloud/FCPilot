# handoff.md — FCPilot

## 현재 상태
- Phase: **Sprint 21 완료 (전체 성능 최적화 + 보안/품질 개선)** — 영민 테스트 대기 중
- 마지막 세션: 2026-04-26 (Claude Code)
- Supabase: **ghglnszzjuuvrrwpvhhb** (FCPilot 전용)
- 배포: **fcpilot-kr.streamlit.app** (git push → 자동 반영)

---

## Sprint 1~18 — 완료 (상세는 git log 참조)

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

## Sprint 19 — 완료 (2026-04-20)

### 보안 강화
- [x] `utils/security.py` 신규 — brute force 차단(5회/5분, 10분 잠금) + 입력 검증(SQL injection/XSS 패턴) + Storage 경로 검증(path traversal 차단)
- [x] `auth.py` 로그인 brute force 차단 적용
- [x] `auth.py` fail-open → fail-closed (DB 장애 시 approved → pending)
- [x] `auth.py` 비밀번호 찾기(재설정) 기능 추가 (Supabase reset_password_email)
- [x] `db_migrate.py` exec_sql RPC anon/authenticated 권한 차단 마이그레이션 추가
- [x] `page_clients_detail.py` Storage 다운로드 경로 검증 (validate_storage_path)
- [x] `page_pioneer_ocr.py` create_client 직접 호출 → get_admin_client 통합
- [x] `migration.py` DB 에러 원문 노출 차단
- [x] DB: 12/12 테이블 RLS 활성화 (bot_sessions service_role_only 포함)
- [x] DB: exec_sql 함수 anon/authenticated 실행 권한 차단

### 보안 수정 (에러 노출 + XSS)
- [x] `page_clients_remind.py:57` DB 에러 원문 → 안전한 메시지
- [x] `page_home.py:184` DB 에러 원문 → 안전한 메시지
- [x] `page_home_forms.py:107` DB 에러 원문 → 안전한 메시지
- [x] `geocoding.py:78` API 에러 객체 → 안전한 메시지
- [x] `calendar_render.py:149` DB값 esc() 적용 (XSS 차단)

### 데드 파일 삭제
- [x] `services/yakwan_analyzer.py` 삭제 (yakwan_engine.py로 대체됨)
- [x] `utils/naver_map.py` 삭제 (kakao_map.py로 대체됨)

### 데드코드 제거
- [x] `helpers.py` mask_name, mask_phone 미사용 함수 제거
- [x] `telegram.py` notify_sprint_complete 외 3개 미사용 함수 제거
- [x] `kakao_map.py` PolyLineTextPath 미사용 import 제거
- [x] `map_utils.py` create_map, create_route_map 미사용 함수 제거
- [x] `db_admin.py` table_exists, run_sql* 등 5개 미사용 함수 제거
- [x] `config.py` APP_VERSION, ALLOWED_FILE_TYPES 미사용 상수 제거
- [x] `page_analysis_yakwan.py` k_column_data 미사용 변수 제거

### 중복 상수 통합 → config.py
- [x] TOUCH_OPTIONS (4곳 → config.py 1곳)
- [x] CATEGORY_OPTIONS (3곳 → config.py 1곳)
- [x] INSURANCE_CATEGORIES + INSURANCE_CAT_ICON (2곳 → config.py 1곳)

### excel_generator.py 리팩터링 (724줄 → 365줄)
- [x] `services/excel_helpers.py` 신규 (110줄) — safe_val, 병합, 서식 복사, classify_renewal
- [x] `services/excel_review.py` 신규 (277줄) — 갱신/리뷰 섹션, build_review, 실손 세대 판별
- [x] `_fill_renewal`/`_fill_renewal_all` 중복 로직 → `classify_renewal()` 통합

### 성능 최적화
- [x] `page_stats_products.py` O(N²) → O(N) 집계 (단일 패스로 premium_sum 누적)
- [x] `page_clients.py` contact_logs 풀 로드 → in_("client_id", ids) 범위 한정

### 기타
- [x] `app.py` __import__("html").escape → esc() 교체
- [x] `app.py` except Exception: pass → logging 추가
- [x] `page_clients.py` import 순서 정리
- [x] `page_clients_detail.py` print 4곳 → logging 교체
- [x] `tests/test_all.py` 삭제된 yakwan_analyzer 참조 제거

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

## 보안 현황 (Sprint 19 기준)

| 항목 | 상태 |
|------|------|
| RLS | 12/12 테이블 활성화 |
| exec_sql | anon/authenticated 차단 |
| Brute force | 5회/5분 + 10분 잠금 |
| XSS | esc() 전면 적용 |
| 에러 노출 | safe_error 전면 적용 |
| Path traversal | validate_storage_path 적용 |
| 보안 등급 | **A** |

---

## Sprint 20 — 완료 (2026-04-21)

### PDF 파싱 세로(Portrait) 지원
- [x] `pdf_extractor.py` 세로 포맷 계약 테이블 파싱 (6열, 2행/계약)
- [x] `pdf_extractor.py` 세로 포맷 보장금액 테이블 파싱 (4열 item + 4열 data)
- [x] `pdf_extractor_detail.py` 세로 포맷 상세페이지 탐색 범위 확장

### 파싱 오매핑 수정
- [x] `item_map.py` 운전자보험 교통상해사망 매핑 제외 (None)
- [x] `item_map.py` 짧은 키 정리 ("치매", "수술비", "사망" 등 2~3글자 제거)
- [x] `item_map.py` 운전자/화재보험 전용 특약 무시 항목 추가
- [x] `item_map.py` 질병수술(최대) 별도 행(row 56) 분리
- [x] `pdf_extractor_detail.py` 2차 보완 가드 강화 (seen_rows 항목은 0이어도 덮어쓰기 금지)
- [x] `pdf_extractor_detail.py` verify 함수 카테고리명 필터링 + 페이지간 중복 방지

### 테스트
- [x] `test_parsing.py` v13 템플릿 행번호 반영 (SUM→L열, 갱신→87, 리뷰→92, 기납입→82)
- [x] `test_pdf_batch.py` 신규 — tests/pdfs/ 폴더 PDF 일괄 파싱 검증 도구

### Git 설정
- [x] 프로젝트별 GitHub 계정 분리 (FCPilot/WaveBot→daecan110-cloud, AlphaBot→japanstudy1205-cloud)

---

## Sprint 21 — 완료 (2026-04-26)

### 성능 최적화 (10건)
- [x] `supabase_client.py` set_session 5분 간격 호출 (매 rerun HTTP 왕복 제거)
- [x] `fp_reminder_service.py` fp_reminders 2쿼리→1쿼리 통합 + @st.cache_data(ttl=30)
- [x] `db_migrate.py` TCP 타임아웃 5→2초 + 성공 주소 session_state 캐싱
- [x] `page_stats_products.py` 3개 로드 함수 @st.cache_data(ttl=60)
- [x] `page_clients_timeline.py` _collect_events 4테이블 @st.cache_data(ttl=30)
- [x] `calendar_render.py` 월간 리마인드 조회 캐싱 분리
- [x] `page_pioneer_share.py` shop_counts N+1→.in_() 배치 쿼리
- [x] `page_pioneer_map.py` _render_map @st.fragment 격리 + 탭 lazy 로딩
- [x] `page_home_forms.py` 최근 활동 쿼리 캐싱
- [x] `kakao_map.py` st_folium→components.html 경량 렌더링

### 보안/품질 (6건)
- [x] scripts/ 3파일 API 키 하드코딩→환경변수 + .gitignore 추가
- [x] `excel_helpers.py` 상수 6개 통합 (excel_generator↔excel_review 이중정의 제거)
- [x] 통계/방문기록 silent fail에 st.warning 추가
- [x] `page_analysis.py` 전체선택/해제 on_click 콜백 전환 (불필요 rerun 제거)
- [x] 날짜 esc() 미적용 수정 (calendar_render, pioneer_history)
- [x] Hook에 카카오 API 키 패턴 추가

### DB 마이그레이션
- [x] `022_analysis_client_id.sql` — analysis_records에 client_id FK + 인덱스 추가
- [x] `db_migrate.py`에 자동 마이그레이션 등록

### 문서/설정
- [x] SECURITY.md 삭제된 함수(mask_name/mask_phone) 참조 정리
- [x] RULES_DETAIL.md DB 테이블 목록 동기화 (client_contracts, pioneer_shares 추가)
- [x] Memory 시스템 초기화 (MEMORY.md + 5개 메모리 파일)

---

## 알려진 이슈

- Gemini 무료 tier: 분당 2회 제한 → 429 시 자동 재시도 대응 완료
- PDF 검증 경고 일부 잔존 (진단표 vs 보장금액표 기준 차이) — 추가 PDF 데이터로 개선 예정
- 200줄 초과 파일 15개 — 대형 리팩터링 별도 Sprint 필요

---

## 다음 세션 시작 시

1. `git pull origin main`
2. 실사용 피드백 수집 (특히 지도/홈 속도 체감 개선 여부)
3. analysis_records client_id 마이그레이션 적용 확인
