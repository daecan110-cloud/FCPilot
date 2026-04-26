---
name: db-health
description: >
  DB 상태 점검 자동화. "DB 점검", "데이터 정리", "고아 데이터", "DB 상태" 요청 시 활성화.
  테이블별 row count, RLS, 참조 무결성, 인덱스, 마이그레이션 상태를 확인한다.
---

## 점검 절차

### 1. 테이블별 상태 확인
Supabase 클라이언트로 각 테이블 row count 조회:
```python
from utils.supabase_client import get_supabase_client
sb = get_supabase_client()
tables = [
    "users_settings", "clients", "contact_logs", "analysis_records",
    "pioneer_shops", "pioneer_visits", "yakwan_records", "command_queue",
    "bot_sessions", "fp_products", "fp_reminders", "client_contracts",
    "pioneer_shares",
]
for t in tables:
    res = sb.table(t).select("id", count="exact").execute()
    print(f"{t}: {res.count}건")
```

### 2. 참조 무결성 검사
고아 데이터 탐지 (부모 레코드 없는 자식):
- `contact_logs.client_id` → `clients.id`
- `fp_reminders.client_id` → `clients.id`
- `client_contracts.client_id` → `clients.id`
- `pioneer_visits.shop_id` → `pioneer_shops.id`
- `pioneer_shares.owner_id` / `shared_with_id` → `auth.users`

### 3. RLS 상태 확인
anon 키로 직접 접근 시도 → 빈 결과 반환되는지 확인 (이미 test_all.py에서 검증)

### 4. 마이그레이션 상태
`utils/db_migrate.py`의 `_MIGRATIONS` 목록과 실제 DB 스키마 비교:
- 컬럼 존재 여부 (`fp_reminders.result`, `analysis_records.client_id` 등)

### 5. 인덱스 확인
`sql/` 폴더의 CREATE INDEX 문과 실제 적용 여부 대조

## 출력 형식
```
📊 DB 상태 보고서
─────────────────
테이블 현황: 13개 테이블, 총 XXX건
고아 데이터: 0건 (또는 발견 시 상세)
RLS: 13/13 활성화
마이그레이션: 모두 적용됨 (또는 미적용 항목)
```

## 주의사항
- 데이터 삭제/수정은 하지 마. 보고만 한다.
- 고아 데이터 발견 시 삭제 SQL을 제시하되 영민 확인 후 실행.
- `get_supabase_client()`는 인증된 사용자 컨텍스트이므로 자기 데이터만 조회 가능.
  전체 점검이 필요하면 `utils/db_admin.py`의 `get_admin_client()` 사용.
