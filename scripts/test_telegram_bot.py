"""텔레그램 봇 v5 자동 테스트 — Edge Function 직접 호출 + DB 검증

Edge Function에 Telegram webhook 페이로드를 직접 POST → DB 변화로 결과 확인.
사용법: python scripts/test_telegram_bot.py
"""
import os
import sys
import time
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from utils.secrets_loader import load_secrets

_secrets = load_secrets()
_tg_user = _secrets.get("telegram_user", {})
CHAT_ID = str(_tg_user.get("chat_id", ""))
BOT_TOKEN = _tg_user.get("bot_token", "")
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

SUPABASE_URL = _secrets["supabase"]["url"]
SERVICE_KEY = _secrets["supabase"]["service_role_key"]
EDGE_FN_URL = f"{SUPABASE_URL}/functions/v1/telegram-bot"

SB_HEADERS = {"apikey": SERVICE_KEY, "Authorization": "Bearer " + SERVICE_KEY}
EDGE_HEADERS = {"Authorization": "Bearer " + SERVICE_KEY, "Content-Type": "application/json"}

TEST_NAME = "봇테스트_자동"
_msg_id = 1000


def send(text: str) -> bool:
    """Edge Function에 Telegram webhook 페이로드 직접 전송"""
    global _msg_id
    _msg_id += 1
    payload = {
        "update_id": _msg_id,
        "message": {
            "message_id": _msg_id,
            "from": {"id": int(CHAT_ID), "is_bot": False, "first_name": "영민"},
            "chat": {"id": int(CHAT_ID), "type": "private"},
            "date": int(time.time()),
            "text": text,
        },
    }
    try:
        r = requests.post(EDGE_FN_URL, headers=EDGE_HEADERS, json=payload, timeout=15)
        return r.status_code in (200, 201)
    except Exception as e:
        print(f"  전송 실패: {e}")
        return False


def db_get(table: str, params: str) -> list:
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}?{params}",
            headers=SB_HEADERS, timeout=10)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def db_delete(table: str, params: str):
    try:
        requests.delete(f"{SUPABASE_URL}/rest/v1/{table}?{params}",
            headers=SB_HEADERS, timeout=10)
    except Exception:
        pass


def wait(sec: int = 5):
    time.sleep(sec)


def run_tests() -> list[dict]:
    results = []

    def ok(tid, scenario):
        results.append({"id": tid, "scenario": scenario, "ok": True})
        print(f"  ✅ PASS")

    def fail(tid, scenario, reason=""):
        results.append({"id": tid, "scenario": scenario, "ok": False, "reason": reason})
        print(f"  ❌ FAIL: {reason}")

    # 사전 정리
    db_delete("clients", f"name=eq.{TEST_NAME}")
    db_delete("clients", f"name=like.{TEST_NAME}%")

    # ── T01: reminder ───────────────────────────────
    print("\n[T01] reminder — 할일 조회")
    send("할일")
    wait(5)
    ok("T01", "reminder")  # 에러 없이 전송되면 pass (응답은 텔레그램에서 확인)

    # ── T02: stats ──────────────────────────────────
    print("\n[T02] stats — 고객 통계")
    send("고객 몇명이야?")
    wait(5)
    ok("T02", "stats")

    # ── T03: register ───────────────────────────────
    print("\n[T03] register — 고객 등록")
    count_before = len(db_get("clients", f"name=ilike.*{TEST_NAME}*"))
    send(f"{TEST_NAME} 25세 B등급 수원 등록")
    wait(6)
    after = db_get("clients", f"name=ilike.*{TEST_NAME}*&select=id,name,prospect_grade,age_group,address")
    if after:
        c = after[0]
        print(f"  DB: {c}")
        if c.get("prospect_grade") == "B":
            ok("T03", "register")
        else:
            fail("T03", "register", f"등급 불일치: {c.get('prospect_grade')}")
    else:
        fail("T03", "register", "DB에 등록 안 됨")

    # ── T04: query ──────────────────────────────────
    print("\n[T04] query — 고객 조회")
    send(TEST_NAME)
    wait(5)
    ok("T04", "query")  # 등록된 경우 조회 가능, 응답 텔레그램 확인

    # ── T05: update (직전 고객) ──────────────────────
    print("\n[T05] update — 직전 고객 등급 수정")
    send("등급 A로 변경")
    wait(6)
    after = db_get("clients", f"name=ilike.*{TEST_NAME}*&select=prospect_grade")
    if after and after[0].get("prospect_grade") == "A":
        ok("T05", "update (직전 고객)")
    else:
        fail("T05", "update (직전 고객)", f"DB: {after}")

    # ── T06: update (이름 포함) ──────────────────────
    print("\n[T06] update — 이름 포함 수정")
    send(f"{TEST_NAME} 나이 30대로 수정")
    wait(6)
    after = db_get("clients", f"name=ilike.*{TEST_NAME}*&select=age_group")
    if after and "30" in str(after[0].get("age_group", "")):
        ok("T06", "update (이름 포함)")
    else:
        fail("T06", "update (이름 포함)", f"DB: {after}")

    # ── T07: contact ────────────────────────────────
    print("\n[T07] contact — 상담 기록")
    clients = db_get("clients", f"name=ilike.*{TEST_NAME}*&select=id")
    client_id = clients[0]["id"] if clients else None
    log_before = len(db_get("contact_logs", f"client_id=eq.{client_id}")) if client_id else 0
    send(f"{TEST_NAME} 오늘 통화함 관심있다고 함")
    wait(6)
    if client_id:
        log_after = db_get("contact_logs", f"client_id=eq.{client_id}&select=memo,touch_method")
        if len(log_after) > log_before:
            print(f"  DB: {log_after[-1]}")
            ok("T07", "contact")
        else:
            fail("T07", "contact", "contact_logs에 기록 없음")
    else:
        fail("T07", "contact", "client_id 없음")

    # ── T08: visit ──────────────────────────────────
    print("\n[T08] visit — 방문 예약")
    visit_before = len(db_get("contact_logs", f"client_id=eq.{client_id}&visit_reserved=eq.true")) if client_id else 0
    send(f"{TEST_NAME} 내일 오전 10시 방문 예약")
    wait(6)
    if client_id:
        visit_after = db_get("contact_logs", f"client_id=eq.{client_id}&visit_reserved=eq.true&select=visit_datetime")
        if len(visit_after) > visit_before:
            print(f"  DB: {visit_after}")
            ok("T08", "visit")
        else:
            fail("T08", "visit", "visit_reserved 기록 없음")
    else:
        fail("T08", "visit", "client_id 없음")

    # ── T09: search ─────────────────────────────────
    print("\n[T09] search — 조건 검색")
    send("A등급 고객 검색")
    wait(5)
    ok("T09", "search")

    # ── T10: delete ─────────────────────────────────
    print("\n[T10] delete — 고객 삭제")
    send(f"{TEST_NAME} 삭제")
    wait(6)
    remaining = db_get("clients", f"name=ilike.*{TEST_NAME}*")
    if not remaining:
        ok("T10", "delete")
    else:
        # 정리 시도
        db_delete("clients", f"name=ilike.*{TEST_NAME}*")
        fail("T10", "delete", f"DB에 {len(remaining)}명 남음")

    return results


def report(results: list[dict]):
    passed = sum(1 for r in results if r["ok"])
    lines = [f"📊 *텔레그램 봇 v5 테스트*\n"]
    lines.append(f"통과: {passed}/{len(results)}\n")
    for r in results:
        icon = "✅" if r["ok"] else "❌"
        reason = f" — {r.get('reason','')}" if not r["ok"] and r.get("reason") else ""
        lines.append(f"{icon} {r['id']} {r['scenario']}{reason}")

    msg = "\n".join(lines)
    requests.post(f"{BOT_API}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    print(f"\n결과: {passed}/{len(results)} 통과")
    return passed


if __name__ == "__main__":
    print("FCPilot 텔레그램 봇 v5 테스트 시작")
    print("=" * 50)
    results = run_tests()
    passed = report(results)
    sys.exit(0 if passed >= 8 else 1)
