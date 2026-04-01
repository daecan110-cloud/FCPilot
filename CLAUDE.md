# CLAUDE.md — FCPilot

## 정체성
보험 FC 업무 통합 플랫폼 (보장분석+CRM+개척+약관)
사용자: 신한라이프 FC 영민 + 향후 동료 FC

## 기술 스택
Streamlit / Supabase / Claude API / Gemini / Naver Maps / Telegram / openpyxl

## 코드 규칙 (절대 위반 금지)
- 한 파일 200줄 이하, 한 역할. 넘으면 쪼개기
- bare except 금지 → `except Exception as e:`
- 새 기능 = 새 파일. app.py에 로직 넣지 마
- import 순서: 표준 → 서드파티 → 로컬
- 개인정보/API키 커밋 금지 → .gitignore, secrets.toml

## 파일 구조
```
app.py → 라우터만 / auth.py → 인증만 / config.py → 설정만
views/ → UI / services/ → 로직 / utils/ → 유틸
sql/ → 마이그레이션 / templates/ → 정적 파일
```

## 세션 규칙
- 시작: git pull → plan.md → handoff.md → 대상 파일 읽기
- 종료: handoff.md 업데이트 → plan.md 체크 → commit+push
- 테스트: Sprint 완료 시 / 3개+ 파일 변경 시 → `python tests/test_all.py`

## 스크린샷
경로: `C:\FCPilot\screenshots\` (고정)
"캡처 N장 봐줘" → 최신순 정렬 후 지정 장수만큼 읽기
장수 미지정 시 먼저 물어보기

## 상세 규칙 참조
- DB/보안/텔레그램/작업쪼개기/Sprint완료 → `docs/RULES_DETAIL.md`
- 보안 체크리스트 → `SECURITY.md`
