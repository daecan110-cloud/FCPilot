"""신한라이프 tool 엑셀 → Supabase 마이그레이션

사용법:
    python scripts/migrate_excel.py --dry-run   # 결과 미리보기 (기본값)
    python scripts/migrate_excel.py --run       # 실제 저장

대상 시트: '보험 DB터치'
저장 테이블: clients + contact_logs
"""
import os
import sys
import argparse
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import openpyxl
import requests
from utils.secrets_loader import load_secrets

EXCEL_PATH = r"c:\Users\youngmin\Downloads\신한라이프 tool의 사본.xlsx"
SHEET_NAME = "보험 DB터치"

_secrets = load_secrets()
SUPABASE_URL = _secrets["supabase"]["url"]
SERVICE_KEY = _secrets["supabase"]["service_role_key"]
SB_HEADERS = {"apikey": SERVICE_KEY, "Authorization": "Bearer " + SERVICE_KEY,
              "Content-Type": "application/json", "Prefer": "return=representation"}

FC_ID = _secrets.get("app", {}).get("admin_fc_id", "")

# 등급 매핑: 엑셀 값 → DB CHECK 제약 (A/B/C/D)
GRADE_MAP = {
    "A 등급": "A", "A등급": "A",
    "B 등급": "B", "B등급": "B",
    "C 등급": "C", "C등급": "C",
    "D 등급": "D", "D등급": "D",
    "관심등급": "C",   # 당장은 C로, 추후 별도 등급 추가 가능
    "F등급":   "D",   # 가장 낮은 등급
}


# ── 엑셀 파싱 ────────────────────────────────────────────

def load_rows() -> list[dict]:
    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    ws = wb[SHEET_NAME]
    all_rows = list(ws.iter_rows(values_only=True))

    # 0행: 헤더, 1행: 예시(ex)), 2행~: 실제 데이터
    header = [str(h).strip() if h else "" for h in all_rows[0]]
    records = []
    for row in all_rows[2:]:
        if not any(row):
            continue
        records.append(dict(zip(header, row)))
    return records


def parse_row(rec: dict) -> dict | None:
    name = _str(rec.get("이름"))
    if not name:
        return None

    phone_raw = _str(rec.get("휴대폰"))
    age_raw   = _str(rec.get("나이"))
    address   = _str(rec.get("지역"))
    occupation = _str(rec.get("직업"))
    grade_raw = _str(rec.get("가망고객등급"))
    db_source = _str(rec.get("DB종류"))
    memo_raw  = _str(rec.get("상담내용"))
    touch_method = _str(rec.get("터치방식"))
    last_contact = rec.get("최근연락 날짜")

    # 등급 정규화
    grade = GRADE_MAP.get(grade_raw, "C")

    # 나이 정규화 (age_group 컬럼: '50대', '30대' 등 자유 텍스트)
    age_group = age_raw if age_raw and age_raw != "잘 모름" else None

    # fallback_date: 최근연락 날짜 → 오늘
    fallback = _to_date(last_contact) or date.today()

    return {
        "client": {
            "fc_id":          FC_ID,
            "name":           name,
            "phone_encrypted": _encrypt_phone(phone_raw),
            "phone_last4_hash": _hash_last4(phone_raw),
            "age_group":      age_group,
            "occupation":     occupation,
            "address":        address,
            "prospect_grade": grade,
            "db_source":      db_source,
            "memo":           "",   # 상담 내용은 contact_logs에 저장
        },
        "memo_raw":    memo_raw,
        "touch_method": touch_method,
        "fallback_date": fallback,
    }


# ── DB 저장 ──────────────────────────────────────────────

def insert_client(client: dict, dry_run: bool) -> str | None:
    if dry_run:
        return "DRY_RUN_ID"
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/clients",
        headers=SB_HEADERS,
        json=client,
        timeout=10,
    )
    if r.status_code in (200, 201):
        return r.json()[0]["id"]
    raise RuntimeError(f"clients insert 실패: {r.status_code} {r.text[:200]}")


def insert_contact_logs(
    client_id: str,
    logs: list[dict],
    dry_run: bool,
) -> int:
    if not logs:
        return 0
    if dry_run:
        return len(logs)

    # 마이그레이션은 service key로 직접 insert (RLS 우회)
    saved = 0
    for log in logs:
        row: dict = {
            "client_id": client_id,
            "fc_id": FC_ID,
            "memo": log["memo"],
            "touch_method": log.get("touch_method", ""),
        }
        contact_date = log.get("contact_date")
        if contact_date:
            row["created_at"] = datetime.combine(
                contact_date, datetime.min.time()
            ).isoformat()
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/contact_logs",
            headers=SB_HEADERS,
            json=row,
            timeout=10,
        )
        if r.status_code in (200, 201):
            saved += 1
        else:
            print(f"  ⚠️ contact_log 오류: {r.status_code} {r.text[:100]}")
    return saved


# ── 실행 ─────────────────────────────────────────────────

def run(dry_run: bool):
    from services.contact_log_parser import parse_memo_to_logs

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}마이그레이션 시작")
    print("=" * 55)

    records = load_rows()
    parsed  = [r for r in (parse_row(rec) for rec in records) if r]
    print(f"유효 고객: {len(parsed)}명\n")

    total_clients = 0
    total_logs    = 0
    errors        = []

    for p in parsed:
        try:
            client_id = insert_client(p["client"], dry_run)
            total_clients += 1

            logs = parse_memo_to_logs(
                p["memo_raw"],
                fallback_date=p["fallback_date"],
                touch_method=p["touch_method"],
            )
            log_count = insert_contact_logs(client_id, logs, dry_run)
            total_logs += log_count

            # 로그 미리보기 (dry-run 또는 상담 내용 있을 때)
            name = p["client"]["name"]
            grade = p["client"]["prospect_grade"]
            if logs:
                print(f"  ✅ {name} ({grade}) — 상담 {log_count}건")
                if dry_run:
                    for lg in logs:
                        d = lg["contact_date"] or "날짜미상"
                        print(f"     [{d}] {lg['memo'][:50]}")
            else:
                print(f"  ✅ {name} ({grade})")

        except Exception as e:
            errors.append(f"{p['client']['name']}: {e}")
            print(f"  ❌ {p['client']['name']}: {e}")

    print(f"\n{'─' * 55}")
    print(f"고객 저장: {total_clients}명")
    print(f"상담 이력: {total_logs}건")
    if errors:
        print(f"오류: {len(errors)}건")
    if dry_run:
        print("\n※ dry-run 완료. 실제 저장하려면 --run 옵션 사용")


# ── 유틸 ─────────────────────────────────────────────────

def _str(v) -> str:
    return str(v).strip() if v is not None and str(v).strip() not in ("", "None", "-") else ""


def _to_date(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return None


def _encrypt_phone(phone: str) -> str:
    if not phone:
        return ""
    try:
        from services.crypto import encrypt_phone
        return encrypt_phone(phone)
    except Exception:
        return ""


def _hash_last4(phone: str) -> str:
    if not phone:
        return ""
    try:
        from services.crypto import hash_phone_last4
        return hash_phone_last4(phone)
    except Exception:
        return ""


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", default=True,
                       help="결과 미리보기 (저장 안 함, 기본값)")
    group.add_argument("--run", action="store_true",
                       help="실제 DB에 저장")
    args = parser.parse_args()

    dry_run = not args.run
    run(dry_run=dry_run)
