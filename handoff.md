# handoff.md — FCPilot

## 현재 상태
- Phase: **Sprint 8C Round 2 완료 + 통계 개선 + 버그픽스**
- 마지막 세션: 2026-03-31 (Claude Code)
- Supabase: **ghglnszzjuuvrrwpvhhb** (FCPilot 전용)

## Sprint 1~7 — 완료

---

## Sprint 8 완료 내역

### Phase 1: 엑셀 마이그레이션 — 완료
- [x] `신한라이프 tool의 사본.xlsx` → clients 99명 + contact_logs 34건 이관
- [x] `scripts/migrate_excel.py` 작성 (dry-run/run 모드)
- [x] FC_ID: `ee41ae34-feef-4689-b005-f144cab4e4a6` (김영민fc)

### Phase 2: Sprint 8B 버그픽스 — 완료 (commit: 56bd463)
- [x] BUG-01: `source` → `db_source` 컬럼명 수정
- [x] BUG-02: `contact_type`/`content` → `touch_method`/`memo`
- [x] BUG-03: 새로고침/뒤로가기 로그아웃 → `streamlit-cookies-controller` 쿠키 기반 세션 복원 (commit: 09bf70a)
- [x] BUG-04: 전화번호 표시 형식 수정
- [x] BUG-05: OCR 프롬프트 개선 + 업종 드롭다운
- [x] BUG-06: EXIF GPS → Naver Reverse Geocoding 주소 자동 추출
- [x] BUG-07: 매장 클릭 → 지도 center 이동 (session_state 기반)
- [x] BUG-08: `fp_pioneer_shops` → `pioneer_shops` 조인 수정 + 팔로업 개선
- [x] UX-01: 출처 → 유입경로 라벨
- [x] UX-02: 고객 목록 필터 (나이대/지역/상담유무/정렬)
- [x] UX-03: 업종 드롭다운 (BUG-05에 포함)
- [x] UX-04: 영업 모드별 탭 순서 변경
- [x] UX-05: CSV 가져오기 → 설정 탭으로 이동

### Phase 3: Sprint 8C Round 1 — 완료 (commit: b69d9e7)
- [x] 전화번호 마스킹 제거 (상세 화면에서 원본 표시)
- [x] 상담 이력 삭제 (2-step 확인)
- [x] 고객 삭제 버튼 (목록 + 상세 양쪽)
- [x] 보장분석 자동 저장 + 통계 0건 수정 (count="exact")

### Phase 4: Sprint 8C Round 2 — 완료 (commits: 9ff197f~82c9b37)
- [x] 등급 판별 기준 안내 (VIP/S/A/B/C/D 설명 expander)
- [x] 약관 PDF 동시 업로드 + AI 상담 대화창 (page_analysis.py 재구성)
- [x] 고객 목록 정렬 드롭다운 (메인 행 4번째 컬럼)
- [x] gender 빈 문자열 ValueError 수정
- [x] 약관 분석 429 rate limit → 자동 재시도 + 카운트다운
- [x] 유입경로 카테고리 커스터마이징 (설정 탭 + users_settings.source_categories JSONB)
- [x] 정렬 설정 DB 영구 저장 (users_settings.clients_sort, commit: 7ed4995)

### Phase 5: 통계 대시보드 개선 — 완료 (commit: 19420a3)
- [x] 등급 카드 6개: VIP🟣/S🟢/A🔴/B🟠/C🔵/D⚫ (전체 기준)
- [x] 기간별 신규 고객 수 (created_at 필터)
- [x] 기간당 평균 상담: 총 건수 + 일 평균
- [x] 고객 분포 드롭다운: 등급별/유입경로별/나이대별/지역별

### Phase 6: 텔레그램 알림 수정 — 완료 (commit: e9970bc)
- [x] send_message 사일런트 실패 제거
- [x] 성공: `[TELEGRAM] OK: 200` 출력
- [x] 실패: `[TELEGRAM] FAIL: <코드> <내용>` 출력
- [x] Markdown 400 오류 시 plain text 자동 재시도

---

## Sprint 8C Round 3 — 미완료 (다음 세션)
- [ ] 매장 수정 + 삭제 (pioneer_shops)
- [ ] 팔로업 수정 + 삭제 (contact_logs / pioneer_visits)
- [ ] 간판 OCR 주소 자동입력 (Naver Search Local 폴백)
- [ ] 동선기록 이전 기록 달력 하이라이트

## 알려진 이슈
- Gemini 무료 tier: 분당 2회 제한 → 429 시 재시도 대응
- 200줄 초과 파일: page_clients.py(428줄), page_analysis.py 등 — 향후 분리 예정
- UX-06: 약관분석 AI 대화창 P2 deferred (구현 틀은 있음, 정교화 필요)

## 배포 상태
- **fcpilot-kr.streamlit.app** — 자동 배포 (git push → 자동 반영)
- requirements.txt: `streamlit-cookies-controller>=0.0.4` (extra-streamlit-components 교체)

## DB 스키마 변경 이력 (이번 세션)
| 테이블 | 변경 | 용도 |
|--------|------|------|
| users_settings | `source_categories JSONB` 추가 | 유입경로 카테고리 커스터마이징 |
| users_settings | `clients_sort TEXT` 추가 | 정렬 설정 영구 저장 |

## 다음 세션 시작 시
1. `git pull origin main`
2. Sprint 8C Round 3 시작: `매장 수정/삭제` 먼저
3. 실사용 피드백 수집 병행
