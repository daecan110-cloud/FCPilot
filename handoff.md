# handoff.md — FCPilot

## 현재 상태

**Phase:** Sprint 2 완료 (CRM + 개척 핵심)
**마지막 세션:** 2026-03-31 (Opus — 전체 문서 검토 + Sprint 3 설계)

---

## Sprint 1 (MVP) — 완료

- [x] 프로젝트 초기화 (repo, 파일 구조, requirements.txt)
- [x] Supabase 테이블 생성 (fp_users_settings, fp_clients, fp_contact_logs, fp_analysis_records)
- [x] Auth 구현 (로그인/회원가입/세션 타임아웃)
- [x] 보장분석 엔진 v4 (PDF → pdfplumber → 엑셀)
- [x] 텔레그램 알림 모듈
- [x] 약관 분석 AI 대화창

### Sprint 1 미해결 (병행 수정)
- [ ] 보장분석표 하단 섹션(가족/세액공제) 셀 병합 패턴 정밀 검증
- [ ] Streamlit Cloud 배포 (fcpilot-kr.streamlit.app)

---

## Sprint 2 (CRM + 개척 핵심) — 구현 완료

- [x] 고객 목록/상세/등록/수정 (page_clients.py)
- [x] 상담 기록 타임라인 (page_clients.py)
- [x] CSV 마이그레이션 (migration.py)
- [x] 간판 OCR — Claude Vision (ocr_engine.py)
- [x] 개척 매장 등록 (page_pioneer_map.py)
- [x] 개척지도 folium (page_pioneer_map.py + map_utils.py)
- [x] Naver 지오코딩 (geocoding.py)
- [x] UI 한국어화 (app.py, page_settings.py)

### Sprint 2 영민 확인 필요
- [ ] Supabase SQL 실행: sql/003_sprint2_tables.sql (fp_pioneer_shops, fp_pioneer_visits)
- [ ] 로컬 테스트: streamlit run app.py → 고객관리/개척지도 탭 확인
- [ ] 실제 간판 사진으로 OCR 테스트
- [ ] 구글시트 CSV 마이그레이션 테스트

---

## 다음 세션 할 일 (Sprint 3: 개척 고도화 + 약관)

- [ ] 동선 추적 탭 (page_pioneer_route.py)
- [ ] 팔로업 플로우 엔진 (followup.py)
- [ ] 약관 분석 전용 탭 (page_yakwan.py + yakwan_engine.py)
- [ ] 리마인드 알림 (reminder.py)
- [ ] Streamlit Cloud 배포

---

## 알려진 이슈

- Supabase project ID: zrtjojphudopwzjpyzoy (AlphaBot과 공유 — fp_ 접두사 분리)
- AlphaBot GitHub repo private 전환 아직 미완료
- Streamlit Cloud 무료 플랜 앱 개수 제한 확인 필요
- 보장분석표 하단 셀 병합 패턴 검증 미완 (Sprint 1 잔여)

---

## 영민에게 물어볼 것

- Supabase SQL 실행 완료 여부
- 구글시트 CSV 파일 준비 여부 (마이그레이션용)
- Naver Developers API 키 발급 완료 여부
- Streamlit Cloud 배포 시점 (Sprint 2 확인 후? Sprint 3 후?)
