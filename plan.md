# plan.md — FCPilot

---

# Sprint 1 (Phase 1: MVP) — 완료

- [x] 프로젝트 초기화 (repo, 파일 구조, requirements.txt)
- [x] Supabase 테이블 생성 (fp_users_settings, fp_clients, fp_contact_logs, fp_analysis_records)
- [x] Auth 구현 (로그인/회원가입/세션 타임아웃)
- [x] 보장분석 탭 (PDF 업로드 → pdfplumber 추출 → 엑셀 생성)
- [x] 보장분석 엔진 v4 (상세 페이지 파싱, 원/만원 변환, 중복 허용)
- [x] 텔레그램 알림 모듈
- [x] 약관 분석 AI 대화창

### 미해결 이슈 (병행 수정)
- [ ] 보장분석표 서식: 하단 섹션(가족/세액공제) 셀 병합 패턴 정밀 검증
- [ ] Streamlit Cloud 배포

---

# Sprint 2 (Phase 2: CRM + 개척) — 완료

## 목표
- [ ] 1. 구글시트 CSV → Supabase 마이그레이션 (fp_clients, fp_contact_logs)
- [ ] 2. 고객 목록/상세 UI (등급·DB종류·터치방식 필터, 상담 타임라인)
- [ ] 3. 고객 등록/수정 폼
- [ ] 4. 상담 내용 기록 (개별 로그)
- [ ] 5. 간판 OCR (Claude Vision → 가게명/주소 추출)
- [ ] 6. 개척 매장 등록 (fp_pioneer_shops)
- [ ] 7. 개척지도 탭 (folium 마커)
- [ ] 8. 모바일 빠른 입력 UI
- [ ] 9. UI 한국어 다듬기 (영업 모드, 개척 등)

## 완료 기준
- 기존 구글시트 데이터 마이그레이션 완료
- 고객 목록 → 상세 → 상담 기록 플로우 정상
- 간판 사진 → 가게명 자동 추출 → 지도 마커 표시
- 모바일에서 메모/고객 등록 가능
- 전체 UI 한국어 자연스럽게

## 건드릴 파일
```
신규:
- pages/page_clients.py        # 고객 목록/상세/등록/수정
- pages/page_pioneer_map.py    # 개척지도 (folium)
- services/ocr_engine.py       # 간판 OCR (Claude Vision)
- services/geocoding.py        # Naver Maps 주소→좌표
- services/migration.py        # CSV→Supabase 마이그레이션
- utils/map_utils.py           # folium 헬퍼

수정:
- app.py                       # 탭 추가 (고객관리, 개척지도)
- config.py                    # Maps API 설정
- pages/page_settings.py       # UI 한국어 수정
```

## Supabase 추가 테이블
```sql
-- fp_pioneer_shops (Sprint 1에서 미생성)
-- fp_pioneer_visits (Sprint 1에서 미생성)
```

## 작업 순서 (의존성 순)
1. Supabase 추가 테이블 SQL (fp_pioneer_shops, fp_pioneer_visits)
2. UI 한국어 다듬기 (app.py, page_settings.py)
3. services/migration.py (CSV 파서)
4. pages/page_clients.py (목록 + 상세 + 등록/수정 + 상담 기록)
5. services/ocr_engine.py (Claude Vision)
6. services/geocoding.py (Naver Maps)
7. pages/page_pioneer_map.py (folium 지도)
8. 모바일 UI 최적화

---

# Sprint 3 (Phase 3: 개척 고도화 + 약관) — 완료

- [x] yakwan_engine.py (약관 PDF → 구조화 JSON + K열 요약)
- [x] page_analysis.py (약관 분석 → I열 반영 → 엑셀 재생성)
- [x] excel_generator.py (k_column_data 지원)
- [x] fp_yakwan_records 테이블 SQL
- [x] map_utils.py (polyline + 번호 마커)
- [x] page_pioneer_route.py (동선 추적 탭)
- [x] app.py (동선기록 탭 추가)
- [x] followup.py (팔로업 상태머신)
- [x] page_pioneer_map.py (팔로업 탭)
- [x] reminder.py (리마인드 대상 조회)

---

# Sprint 4 계획 (Phase 4: 통합 대시보드)

## 건드릴 파일
```
신규:
- pages/page_home.py
- pages/page_stats.py

수정:
- app.py (홈 탭 추가)
```
