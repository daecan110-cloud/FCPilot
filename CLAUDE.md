# CLAUDE.md — FCPilot

## 프로젝트 정체성
FCPilot = 보험 FC 업무 통합 플랫폼 (보장분석 + CRM + 개척영업 + 약관분석)
사용자 = 신한라이프 FC 영민 (개척 주력) + 향후 동료 FC

## 기술 스택
- Frontend: Streamlit
- Backend: Supabase (Seoul, project: zrtjojphudopwzjpyzoy) — `fp_` 접두사 테이블
- AI: Claude API (Sonnet) — 보장분석, 약관, OCR, 어시스턴트
- 지도: folium + Naver Maps API (Search Local + Geocoding)
- 엑셀: openpyxl
- 알림: Telegram Bot API
- 배포: Streamlit Cloud (fcpilot-kr.streamlit.app)

## 코드 규칙 (절대 위반 금지)

1. **한 파일 = 한 역할, 200줄 넘으면 쪼개기**
2. **bare except 금지** → 반드시 `except Exception as e:`
3. **새 기능 = 새 파일** → 기존 파일에 추가하지 않음
4. **Git 커밋 = 작업 단위** → 롤백 가능한 단위
5. **개인정보 파일 커밋 금지** → .gitignore 확인 필수
6. **import 순서**: 표준 → 서드파티 → 로컬

## 파일 구조 (건드리기 전 반드시 확인)

```
app.py              → 라우터/탭 관리만. 로직 넣지 말 것.
auth.py             → Supabase Auth만.
config.py           → 설정/클라이언트 초기화만.
pages/              → 각 탭 UI. 비즈니스 로직은 services/로 분리.
services/           → 핵심 로직. 각 파일 200줄 이내.
utils/              → 공통 유틸.
templates/          → 엑셀 템플릿 등 정적 파일.
```

## 세션 시작 시

1. `plan.md` 읽기 → 오늘 목표 확인
2. `handoff.md` 읽기 → 이전 세션 상태 확인
3. 작업 대상 파일 먼저 읽기 → 수정 전 현재 상태 파악
4. 작업 완료 후 → handoff.md 업데이트 + git commit

## 세션 종료 시

1. handoff.md 업데이트 (완료/미완료/이슈)
2. git add + commit (작업 단위별)
3. plan.md에 완료 체크

## DB 테이블 (fp_ 접두사)

| 테이블 | 역할 |
|--------|------|
| fp_users_settings | FC 설정 (영업 모드 등) |
| fp_clients | 고객 마스터 |
| fp_contact_logs | 상담/터치 이력 |
| fp_pioneer_shops | 개척 매장 |
| fp_pioneer_visits | 개척 방문 기록 (동선) |
| fp_analysis_records | 보장분석 기록 |
| fp_yakwan_records | 약관 분석 기록 |

## 보안 규칙 (절대 위반 금지 — SECURITY.md 참조)

1. **전화번호는 반드시 암호화 저장** → services/crypto.py 사용
2. **print()에 고객 정보 금지** → mask_name(), mask_phone() 사용
3. **Claude API 호출 시 고객명/전화번호 미전송** → 분석 결과만 전송
4. **에러 메시지에 개인정보 금지** → 마스킹 처리
5. **파일 업로드 검증** → PDF/JPG/PNG만, 10MB 이하
6. **매 Sprint 완료 시 보안 체크리스트 실행** → SECURITY.md 스크립트

## 금지 사항

- app.py에 비즈니스 로직 넣기
- 하드코딩 API 키 (secrets.toml 사용)
- 고객 데이터 포함 파일 git commit
- AlphaBot 테이블 접두사 없이 테이블 생성
- plan.md 없이 작업 시작
- 200줄 넘는 파일 방치

## 텔레그램 양방향 소통

### Claude Code → 영민 (알림)
정확히 3가지만:
- ✅ Sprint 완료
- 🔧 영민 직접 확인 필요 (+ ⏳ waiting 메시지)
- ⚠️ Opus 전환 필요

### 영민 → Claude Code (명령)
텔레그램에서 봇에게 메시지 보내면 Claude Code가 읽고 대응:
- "ㅇㅇ" / "진행" → 다음 단계 진행
- "대기" / "잠깐" → 현재 작업 중단 대기
- "상태" → 현재 진행 상황 보고
- "중단" → 현재 Sprint 중단
