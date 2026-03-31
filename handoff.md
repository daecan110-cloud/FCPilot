# handoff.md — FCPilot

## 현재 상태
- Phase: **Sprint 4 완료**
- 마지막 세션: 2026-03-31 (Claude Code)
- Supabase: **ghglnszzjuuvrrwpvhhb** (FCPilot 전용, 접두사 없음)

## Sprint 1~3 — 완료
## Sprint 4 — 완료

### Sprint 4 완료 내역
- [x] 텔레그램 양방향 (getUpdates + 명령어 파싱 + 자유 텍스트 지시)
- [x] utils/db_admin.py (SQL 실행 유틸 + exec_sql RPC)
- [x] K열 약관 분석 UI "K열" 통일 + end-to-end 검증 통과
- [x] pages/page_home.py (홈 대시보드 + 리마인드 트리거)
- [x] pages/page_stats.py (통계 대시보드)
- [x] app.py 탭 7개 (홈/보장분석/고객관리/개척지도/동선기록/통계/설정)
- [x] 리마인드 발송 트리거 (홈 로드 시 하루 1회)
- [x] 세액공제 셀 병합 수정 (D~H 5개 개별, I:K 합계)
- [x] Supabase 새 프로젝트 마이그레이션
  - 구: zrtjojphudopwzjpyzoy (AlphaBot 공유, fp_ 접두사)
  - 신: ghglnszzjuuvrrwpvhhb (FCPilot 전용, 접두사 없음)
- [x] 7개 테이블 생성 + RLS + 트리거 + exec_sql 함수 확인 완료
- [x] 7개 탭 전체 Supabase 연결 확인 완료

---

## 다음 세션 (Sprint 5: 배포 + QA)

1. Streamlit Cloud 배포 (fcpilot-kr.streamlit.app)
2. 전체 QA (모든 탭 실동작 + 모바일)
3. 보안 체크리스트 실행 (SECURITY.md)
4. DB 직접 연결 설정 (Dashboard에서 connection string 확인)
5. 성능 최적화

---

## 알려진 이슈
- DB 직접 연결 미설정 (IPv6 전용 + Pooler 미연결 — connection string 확인 필요)
- Streamlit Cloud 무료 플랜 앱 개수 제한 확인 필요
- 세션 타임아웃: config.py 기준 60분 (SECURITY.md 코드 예시도 통일 완료)
