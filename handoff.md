# handoff.md — FCPilot

## 현재 상태
- Phase: **Sprint 5 진행 중 — 텔레그램 AI 어시스턴트**
- 마지막 세션: 2026-03-31 (Claude Code)
- Supabase: **ghglnszzjuuvrrwpvhhb** (FCPilot 전용)

## Sprint 1~4 — 완료

## Sprint 5 — 진행 중

### 완료
- [x] plan.md Sprint 5 추가 + Gemini API 키 설정
- [x] command_queue 테이블 생성 (exec_sql RPC)
- [x] Supabase Edge Function 프로젝트 초기화
- [x] telegram-bot Edge Function 구현 + 배포
  - Gemini 의도 파악 → 고객 조회/등록/수정 + 리마인드 + 명령큐
- [x] daily-reminder Edge Function 구현 + 배포
- [x] scripts/command_poller.py (로컬 폴링 스크립트)
- [x] 환경변수 설정 (BOT_TOKEN, CHAT_ID, GEMINI_KEY)
- [x] 텔레그램 webhook 설정 완료

### 영민 테스트 필요
- [ ] 텔레그램에서 "오늘 할 일" 보내기 → 리마인드 응답 확인
- [ ] 텔레그램에서 "새 고객: 테스트, 30대, 서울" → 등록 확인
- [ ] 텔레그램에서 "테스트 고객 정보" → 조회 확인
- [ ] python scripts/command_poller.py 실행 → "테스트해줘" 명령 처리 확인

### Daily Reminder cron 설정 필요 (1회)
Supabase Dashboard → Database → Extensions → `pg_cron` + `pg_net` 활성화 후:
```sql
SELECT cron.schedule(
  'daily-reminder',
  '0 0 * * *',
  $$SELECT net.http_post(
    url := 'https://ghglnszzjuuvrrwpvhhb.supabase.co/functions/v1/daily-reminder',
    headers := '{"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoZ2xuc3p6anV1dnJyd3B2aGhiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ5MTk0NDgsImV4cCI6MjA5MDQ5NTQ0OH0.cZpUZmnW2i9ooRcDFnmeaJDAIQ2t_mfN9aHYyxhtvfA"}'::jsonb
  )$$
);
```

---

## 알려진 이슈
- Webhook 설정 시 기존 getUpdates 폴링은 비활성화됨 (양립 불가)
- command_poller.py는 PC 켜져있을 때만 동작
- DB 직접 연결 미설정 (connection string 확인 필요)
