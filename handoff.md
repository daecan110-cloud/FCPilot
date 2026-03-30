# handoff.md — FCPilot

## 현재 상태
- Phase: **Sprint 3 완료 (약관 강화 + 동선 + 팔로업 + 리마인드)**
- 마지막 세션: 2026-03-31 (Claude Code — Sprint 3 구현 완료)

## Sprint 1 (MVP) — 완료
## Sprint 2 (CRM + 개척 핵심) — 완료
## Sprint 3 (약관 강화 + 동선 + 팔로업 + 리마인드) — 완료

### Sprint 2~3 Supabase SQL 실행 필요 (영민이 직접)
- [ ] sql/003_sprint2_tables.sql (fp_pioneer_shops, fp_pioneer_visits)
- [ ] sql/004_yakwan_records.sql (fp_yakwan_records)
- Supabase Dashboard > SQL Editor에서 실행

### 영민 확인 필요
- [ ] streamlit run app.py → 5개 탭 전체 동작 확인
- [ ] 약관 PDF → I열(I~K 병합 셀) 반영 → 엑셀 재다운로드
- [ ] 동선기록 탭 테스트
- [ ] 개척지도 팔로업 탭 테스트
- [ ] 간판 OCR / CSV 마이그레이션 테스트

### 참고: 약관 분석 반영 위치
- 템플릿 Row 74~79의 "특이사항"은 I~K 병합 셀
- K열(col 11)은 MergedCell → 값 입력 불가
- 코드는 I열(col 9)에 값 설정 → 병합 셀 전체에 표시됨
- 사용자 관점: K열 영역에 정상 표시

---

## 다음 세션 (Sprint 4: 통합 대시보드 + 배포)

1. pages/page_home.py — 홈 (오늘의 할 일)
2. pages/page_stats.py — 통계 대시보드
3. app.py 수정 — 홈 탭 추가
4. 리마인드 발송 트리거 (텔레그램 알림)
5. Streamlit Cloud 배포 (fcpilot-kr.streamlit.app)
6. 보장분석표 하단 셀 병합 검증 (Sprint 1 잔여)
7. 전체 QA + 보안 체크리스트

---

## 알려진 이슈
- Supabase: zrtjojphudopwzjpyzoy (AlphaBot 공유 — fp_ 접두사)
- 보장분석표 하단 셀 병합 패턴 검증 미완
- Streamlit Cloud 무료 플랜 앱 개수 제한 확인 필요
