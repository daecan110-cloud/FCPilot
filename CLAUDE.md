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
views/              → 각 탭 UI. 비즈니스 로직은 services/로 분리.
services/           → 핵심 로직. 각 파일 200줄 이내.
utils/              → 공통 유틸.
sql/                → DB 마이그레이션 SQL 파일.
templates/          → 엑셀 템플릿 등 정적 파일.
tests/              → 자동 테스트 스크립트.
scripts/            → 로컬 실행 스크립트 (command_poller 등).
supabase/functions/ → Edge Function (TypeScript/Deno).
```

## 스크린샷 협업

영민이 "최근 스크린샷 봐줘" 또는 "캡처 봐줘" 라고 하면:
```python
# C:\FCPilot\screenshots\ 폴더에서 최근 파일 3개 자동 조회
import glob, os
files = sorted(glob.glob("C:/FCPilot/screenshots/*"), key=os.path.getmtime, reverse=True)[:3]
```
캡처 저장 경로: `C:\FCPilot\screenshots\` (고정)

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

## 텔레그램 알림 규칙

Sprint 완료 또는 영민 확인이 필요한 상황에서 발송한다:

| 상황 | 함수 |
|------|------|
| Sprint 완료 | `notify_sprint_complete(sprint, summary)` |
| 영민 확인 필요 | `notify_action_needed(message)` |
| 에러/경고 | `notify_warning(message)` |

**실행 방법:**
```bash
python -c "
from utils.telegram import send_message
send_message('✅ 메시지 내용')
"
```

## 자동 테스트 규칙

테스트 실행: `python tests/test_all.py`

| 상황 | 테스트 실행 |
|------|------------|
| Sprint 완료 시 | 필수 — 테스트 통과 후 완료 선언 |
| 3개 이상 파일 변경 시 | 필수 — 커밋 전 실행 |
| 영민이 "테스트해줘" | 즉시 실행 |

## DB 테이블

| 테이블 | 역할 |
|--------|------|
| users_settings | FC 설정 (영업 모드, role 등) |
| clients | 고객 마스터 |
| contact_logs | 상담/터치 이력 |
| pioneer_shops | 개척 매장 |
| pioneer_visits | 개척 방문 기록 (동선) |
| analysis_records | 보장분석 기록 |
| yakwan_records | 약관 분석 기록 |
| command_queue | 텔레그램 명령 큐 (Claude Code 제어) |
| bot_sessions | 텔레그램 봇 세션 (Edge Function 상태 저장) |

## DB 작업 규칙

- SQL 실행이 필요하면 항상 db_admin.py로 직접 실행. 영민에게 Supabase Dashboard 가라고 하지 마.
- exec_sql RPC 사용 가능. 테이블 생성, 수정, 데이터 업데이트 전부 Python에서 처리.
- 영민에게 수동 SQL 실행 요청 금지.

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
- 🔧 영민 직접 확인 필요
- ⚠️ 경고/알림

### 영민 → FCPilot 봇 (명령)
- 고객 조회/등록/수정/삭제
- "오늘 할 일" → 리마인드 목록
- 자유 텍스트 → Gemini NLP 처리

## 서브에이전트 한국어 별칭
- "리뷰해줘", "코드 검토" → code-reviewer 서브에이전트 사용
- "분석해줘", "구조 파악", "코드 분석" → codebase-explorer 서브에이전트 사용
- "테스트해줘", "테스트 돌려", "점검해줘" → test-runner 서브에이전트 사용
