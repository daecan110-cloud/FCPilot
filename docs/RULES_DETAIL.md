# 상세 규칙 — CLAUDE.md에서 참조

## 텔레그램 알림

Sprint 완료 또는 영민 확인이 필요한 상황에서 발송:
```bash
python -c "from utils.telegram import send_message; send_message('메시지')"
```
| 상황 | 함수 |
|------|------|
| Sprint 완료 | `notify_sprint_complete(sprint, summary)` |
| 영민 확인 필요 | `notify_action_needed(message)` |
| 에러/경고 | `notify_warning(message)` |

양방향 소통:
- Claude Code → 영민: Sprint 완료 / 확인 필요 / 경고
- 영민 → FCPilot 봇: 고객 조회/등록, 오늘 할 일, 자유 텍스트(Gemini NLP)

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
| command_queue | 텔레그램 명령 큐 |
| bot_sessions | 텔레그램 봇 세션 |
| fp_products | FC 상품 목록 |
| fp_reminders | 리마인드 |
| client_contracts | 기계약자 계약 정보 |
| pioneer_shares | 개척 매장 팀 공유 |

## DB 작업 규칙

- SQL 실행 → 항상 db_admin.py로. 영민에게 Dashboard 가라고 하지 마.
- exec_sql RPC 사용 가능. 테이블 생성/수정/데이터 전부 Python에서 처리.

## 보안 규칙 (SECURITY.md 참조)

1. 전화번호 반드시 암호화 → services/crypto.py
2. print()에 고객 정보 금지 → mask_name(), mask_phone()
3. Claude API 호출 시 고객명/전화번호 미전송
4. 에러 메시지에 개인정보 금지
5. 파일 업로드 → PDF/JPG/PNG만, 10MB 이하
6. Sprint 완료 시 보안 체크리스트 실행

## 작업 쪼개기 규칙

- 한 번에 최대 3개 파일 변경. 넘으면 중간 커밋.
- P0 → P1 → P2 순서 엄수. 한꺼번에 하지 말 것.
- 큰 기능은 Phase A/B/C로 분리 커밋.
- 3개 이상 작업 시 텔레그램 중간 보고.

## Sprint 완료 조건

1. 자동 테스트 통과 (tests/test_all.py)
2. 영민 테스트 체크리스트 텔레그램 발송
3. 영민 확인 전까지 완료 아님 → handoff.md에 "테스트 대기 중" 표시
