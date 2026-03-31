# handoff.md — FCPilot

## 현재 상태
- Phase: **Sprint 4 진행 중 — Supabase 마이그레이션**
- 마지막 세션: 2026-03-31 (Claude Code)
- Supabase: **ghglnszzjuuvrrwpvhhb** (FCPilot 전용, fp_ 접두사 제거)

## Sprint 1~3 — 완료
## Sprint 4 — 진행 중

### 완료
- [x] 텔레그램 양방향 (getUpdates + 명령어 파싱)
- [x] utils/db_admin.py (SQL 실행 유틸)
- [x] K열 약관 분석 UI 텍스트 통일
- [x] pages/page_home.py (홈 대시보드)
- [x] pages/page_stats.py (통계 대시보드)
- [x] app.py 탭 7개
- [x] 리마인드 발송 트리거
- [x] 세액공제 셀 병합 수정
- [x] Supabase 프로젝트 변경 (코드 + secrets.toml + SQL)
  - 구: zrtjojphudopwzjpyzoy (AlphaBot 공유, fp_ 접두사)
  - 신: ghglnszzjuuvrrwpvhhb (FCPilot 전용, 접두사 없음)

### SQL 실행 필요 (1회)
- [ ] sql/005_new_project_all_tables.sql → Supabase SQL Editor에서 실행
  - 7개 테이블 + 3개 함수 + RLS + 트리거 전부 포함
  - DB 직접 연결 안 됨 (IPv6 전용 + Pooler 미연결)

### 영민 확인 필요
- [ ] streamlit run app.py → 7개 탭 동작 확인
- [ ] 회원가입 → users_settings 자동 생성 확인
- [ ] Dashboard → Settings → Database에서 Connection string 확인 (향후 DB 직접 연결용)

---

## 다음 세션 (Sprint 5: 배포 + QA)

1. Streamlit Cloud 배포
2. 전체 QA + 보안 체크리스트
3. DB 직접 연결 설정 (connection string 확인 후)

---

## 알려진 이슈
- DB 직접 연결: IPv6 전용 + Pooler "Tenant or user not found" → connection string 확인 필요
- Streamlit Cloud 무료 플랜 앱 개수 제한 확인 필요
