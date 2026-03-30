# plan.md — FCPilot Sprint 1 (Phase 1: MVP)

## 오늘 목표
- [ ] 프로젝트 초기화 (repo, 파일 구조, requirements.txt)
- [ ] Supabase 테이블 생성 (fp_users_settings, fp_clients, fp_contact_logs, fp_analysis_records)
- [ ] Auth 구현 (로그인/회원가입/역할)
- [ ] 보장분석 탭 기본 UI (PDF 업로드 + 결과 표시)
- [ ] Claude API 보장분석 엔진 연동
- [ ] 엑셀 보장분석표 생성 + 다운로드
- [ ] Streamlit Cloud 배포

## 완료 기준
- `streamlit run app.py` → 로그인 → PDF 업로드 → 엑셀 다운로드 정상 동작
- Supabase에 분석 기록 저장됨
- fcpilot-kr.streamlit.app 접속 가능

## 건드릴 파일
```
신규 생성:
- app.py
- auth.py
- config.py
- pages/page_analysis.py
- pages/page_settings.py
- services/analysis_engine.py
- services/excel_generator.py
- utils/supabase_client.py
- utils/helpers.py
- templates/master_template.xlsx (bogyan에서 복사)
- requirements.txt
- .gitignore
- .streamlit/config.toml

수정 없음:
- CLAUDE.md (이미 완성)
- MASTER.md (이미 완성)
```

## 작업 순서 (의존성 순)
1. repo 초기화 + .gitignore + requirements.txt
2. config.py + supabase_client.py (DB 연결)
3. Supabase 테이블 SQL 실행
4. auth.py (로그인/회원가입)
5. app.py (라우터 + 탭 구조)
6. analysis_engine.py (Claude API 연동)
7. excel_generator.py (openpyxl)
8. page_analysis.py (UI)
9. page_settings.py (모드 전환)
10. Streamlit Cloud 배포

## 주의사항
- master_template.xlsx는 bogyan-analysis-auto/assets/에서 복사
- API 키는 .streamlit/secrets.toml에만 (git 제외)
- Supabase project ID: zrtjojphudopwzjpyzoy (AlphaBot과 동일)
- fp_ 접두사 필수

---

# Sprint 2 계획 (Phase 2: CRM + 개척 핵심)

## 오늘 목표
- [ ] 구글시트 CSV → Supabase 마이그레이션
- [ ] 고객 목록/상세 UI
- [ ] 상담 내용 기록 (fp_contact_logs)
- [ ] 간판 OCR 엔진 (Claude Vision)
- [ ] 개척 매장 등록 (fp_pioneer_shops)
- [ ] 개척지도 탭 (folium)
- [ ] 모바일 빠른 입력 UI

## 완료 기준
- 기존 구글시트 100명 데이터 마이그레이션 완료
- 간판 사진 → 가게명 자동 추출 → 지도 마커 표시
- 모바일에서 메모 입력 가능

## 건드릴 파일
```
신규:
- pages/page_clients.py
- pages/page_pioneer_map.py
- services/ocr_engine.py
- services/geocoding.py
- services/migration.py
- utils/map_utils.py

수정:
- app.py (탭 추가)
- config.py (Maps API 키 추가)
```

---

# Sprint 3 계획 (Phase 3: 개척 고도화 + 약관)

## 건드릴 파일
```
신규:
- pages/page_pioneer_route.py
- pages/page_yakwan.py
- services/yakwan_engine.py
- services/followup.py
- services/reminder.py

수정:
- app.py (탭 추가)
```

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
