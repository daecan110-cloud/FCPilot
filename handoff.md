# handoff.md — FCPilot

## 현재 상태
- Phase: **Sprint 4 완료 (통합 대시보드 + 텔레그램 양방향 + 리마인드)**
- 마지막 세션: 2026-03-31 (Claude Code — Sprint 4 구현)

## Sprint 1 (MVP) — 완료
## Sprint 2 (CRM + 개척 핵심) — 완료
## Sprint 3 (약관 강화 + 동선 + 팔로업 + 리마인드) — 완료
## Sprint 4 (통합 대시보드 + 양방향 + 리마인드 트리거) — 완료

### Sprint 4 완료 내역
- [x] 텔레그램 양방향 (getUpdates 폴링 + 명령어 파싱 + BOT_TOKEN secrets.toml 이전)
- [x] utils/db_admin.py (service_role 클라이언트 + fp_exec_sql RPC 기반 SQL 실행)
- [x] K열 약관 분석 UI 텍스트 통일 (I열→K열)
- [x] pages/page_home.py (홈 대시보드 — 리마인드 + 최근 활동)
- [x] pages/page_stats.py (통계 대시보드 — CRM/개척/분석 통계)
- [x] app.py 탭 7개 (홈/보장분석/고객관리/개척지도/동선기록/통계/설정)
- [x] 리마인드 발송 트리거 (홈 로드 시 하루 1회 텔레그램 알림)
- [x] 세액공제 셀 병합 충돌 수정 (D~H 5개 개별, I:K 합계)

### Supabase SQL 실행 필요 (영민이 직접)
- [ ] sql/000_exec_sql_function.sql (fp_exec_sql 함수 — 1회)
- [ ] sql/003_sprint2_tables.sql (fp_pioneer_shops, fp_pioneer_visits)
- [ ] sql/004_yakwan_records.sql (fp_yakwan_records)
- 순서: 000 → 003 → 004 (Supabase Dashboard SQL Editor에서)

### 영민 확인 필요
- [ ] streamlit run app.py → 7개 탭 전체 동작 확인
- [ ] 홈 탭: 리마인드 목록 + 텔레그램 알림 수신 확인
- [ ] 통계 탭: 기간 필터 + 메트릭 표시 확인
- [ ] 5개 초과 계약 보장분석표 → 세액 섹션 정상 표시 확인

---

## 다음 세션 (Sprint 5: 배포 + QA)

1. Streamlit Cloud 배포 (fcpilot-kr.streamlit.app)
2. 전체 QA (모든 탭 + 모바일)
3. 보안 체크리스트 실행 (SECURITY.md)
4. 텔레그램 양방향 실제 테스트 (poll_loop 통합)
5. 성능 최적화 (불필요한 쿼리 제거)

---

## 알려진 이슈
- Supabase: zrtjojphudopwzjpyzoy (AlphaBot 공유 — fp_ 접두사)
- SQL 003/004 미실행 상태
- Streamlit Cloud 무료 플랜 앱 개수 제한 확인 필요
- SECURITY.md 세션 타임아웃 주석(60분)과 SESSION_TIMEOUT 값(30분) 불일치 — config.py 기준 60분이 맞음
