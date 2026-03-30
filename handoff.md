# handoff.md — FCPilot

## 현재 상태

**Phase:** Sprint 3 완료 (개척 고도화 + 약관)
**마지막 세션:** 2026-03-31

---

## Sprint 1 (MVP) — 완료
## Sprint 2 (CRM + 개척) — 완료
## Sprint 3 (개척 고도화 + 약관) — 완료

- [x] yakwan_engine.py (Claude API → 구조화 JSON + K열 요약)
- [x] page_analysis.py 수정 (약관 분석 → I열 반영 → 엑셀 재생성/재다운로드)
- [x] excel_generator.py (k_column_data 파라미터 지원)
- [x] fp_yakwan_records DB 저장 (sql/004_yakwan_records.sql)
- [x] map_utils.py 확장 (AntPath polyline + 번호 마커)
- [x] page_pioneer_route.py (동선 추적 탭 — 오늘 기록/이전 기록)
- [x] app.py (동선기록 탭 추가 — 총 5탭)
- [x] followup.py (팔로업 상태머신 — 결과별 재방문 기한/우선순위)
- [x] page_pioneer_map.py (팔로업 탭 추가)
- [x] reminder.py (리마인드 대상 조회 — 발송 트리거는 Sprint 4)

---

## 영민 확인 필요

### Supabase SQL 실행 (2개)
1. `sql/003_sprint2_tables.sql` — fp_pioneer_shops, fp_pioneer_visits
2. `sql/004_yakwan_records.sql` — fp_yakwan_records

### 기능 테스트
- 고객관리 탭: 등록/수정/상담기록
- 개척지도 탭: 매장 등록 → 팔로업 확인
- 동선기록 탭: 방문 추가 → 동선 지도
- 보장분석 탭: 약관 PDF → I열 반영 → 엑셀 재다운로드

---

## 미해결 이슈

- 보장분석표 하단 셀 병합 패턴 정밀 검증 (Sprint 1 잔여)
- Streamlit Cloud 배포 미완료
- 텔레그램 양방향 폴링 미구현

---

## 다음 세션 (Sprint 4: 통합 대시보드)

- [ ] page_home.py (대시보드 — 리마인드/팔로업/최근 활동)
- [ ] page_stats.py (통계 — 계약률, 활동량, 매출)
- [ ] 텔레그램 양방향 getUpdates 폴링
- [ ] reminder.py 발송 트리거 (텔레그램 알림)
- [ ] Streamlit Cloud 배포
