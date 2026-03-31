# CLAUDE.md — FCPilot

## 프로젝트 정체성
FCPilot = 보험 FC 업무 통합 플랫폼 (보장분석 + CRM + 개척영업 + 약관분석)
사용자 = 신한라이프 FC 영민 (개척 주력) + 향후 동료 FC

## 기술 스택
- Frontend: Streamlit
- Backend: Supabase (project: ghglnszzjuuvrrwpvhhb) — FCPilot 전용
- AI: Claude API (Sonnet) — 보장분석, 약관, OCR, 어시스턴트
- AI: Gemini API — 텔레그램 봇 자연어 처리
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
tests/              → 자동 테스트 스크립트.
scripts/            → 로컬 실행 스크립트 (command_poller 등).
supabase/functions/ → Edge Function (TypeScript/Deno).
```

## 세션 시작 시

1. `git pull origin main` → 최신 코드 동기화
2. `plan.md` 읽기 → 오늘 목표 확인
3. `handoff.md` 읽기 → 이전 세션 상태 확인
4. 작업 대상 파일 먼저 읽기 → 수정 전 현재 상태 파악

## 세션 종료 시

1. handoff.md 업데이트 (완료/미완료/이슈)
2. plan.md에 완료 체크
3. `git add -A` → `git commit` → `git push origin main`
4. 텔레그램 Sprint 완료 알림 발송

## 텔레그램 자동 알림 규칙 (절대 누락 금지)

매 작업에서 아래 상황 발생 시 **즉시** 텔레그램 알림을 발송한다:

| 상황 | 함수 | 예시 |
|------|------|------|
| git commit 완료 | `send_message("✅ 커밋: {메시지}")` | 파일 수정 후 커밋할 때마다 |
| Sprint 완료 | `notify_sprint_complete(sprint, summary)` | Sprint 종료 시 |
| 영민 확인 필요 | `notify_action_needed(message)` | DB 수동 작업, 키 입력 등 |
| 에러/경고 | `notify_warning(message)` | 빌드 실패, 연결 오류 등 |

**실행 방법:** Python -c로 직접 호출 (Streamlit 컨텍스트 불필요)
```bash
python -c "
from utils.telegram import send_message
send_message('✅ 커밋: 메시지 내용')
"
```

## 자동 테스트 규칙

테스트 실행: `python tests/test_all.py`

| 상황 | 테스트 실행 |
|------|------------|
| Sprint 완료 시 | 필수 — 테스트 통과 후 완료 선언 |
| 3개 이상 파일 변경 시 | 필수 — 커밋 전 실행 |
| 영민이 "테스트해줘" | 즉시 실행 |

테스트 항목: Supabase 연결(7테이블+RPC), 모듈 import(pages+services+utils), config 검증, 템플릿 존재, 문법 체크, fp_ 잔여, 텔레그램 발송
결과는 **항상 텔레그램으로 보고** (--quiet 없이 실행)

## DB 테이블

| 테이블 | 역할 |
|--------|------|
| users_settings | FC 설정 (영업 모드 등) |
| clients | 고객 마스터 |
| contact_logs | 상담/터치 이력 |
| pioneer_shops | 개척 매장 |
| pioneer_visits | 개척 방문 기록 (동선) |
| analysis_records | 보장분석 기록 |
| yakwan_records | 약관 분석 기록 |
| command_queue | 텔레그램 명령 큐 (Claude Code 제어) |

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
- Supabase 테이블명에 불필요한 접두사 사용
- plan.md 없이 작업 시작
- 200줄 넘는 파일 방치

## 텔레그램 양방향 소통

### Claude Code → 영민 (알림)
- ✅ Sprint 완료
- 🔧 영민 직접 확인 필요 (+ ⏳ waiting 메시지)
- ⚠️ 경고/알림
- 📊 상태 보고 (영민이 "상태" 보내면 자동 응답)
- 📩 지시 수신 확인 + ✅ 처리 완료 보고

### 영민 → Claude Code (명령)
텔레그램에서 봇에게 메시지 보내면 Claude Code가 읽고 대응:
- "ㅇㅇ" / "진행" → 다음 단계 진행 (▶️ 확인 응답)
- "대기" / "잠깐" → 현재 작업 중단 대기 (⏸️ 확인 응답)
- "상태" → 현재 진행 상황 텔레그램으로 보고 (📊 자동 응답)
- "중단" → 현재 Sprint 중단 (🛑 확인 응답)
- **그 외 자유 텍스트** → 작업 지시로 처리 (📩 수신 확인 → 실행 → ✅ 결과 보고)

### 작업 중 텔레그램 체크 규칙
- 매 task 완료 후 `check_for_commands()` 호출하여 새 메시지 확인
- `process_commands()`로 자동 응답 + 대기/중단 처리
- 자유 텍스트 지시는 `get_pending_instructions()`로 꺼내서 실행
