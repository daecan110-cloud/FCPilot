"""FCPilot 자동 테스트 스크립트

사용법:
  python tests/test_all.py          # 전체 테스트 + 텔레그램 보고
  python tests/test_all.py --quiet  # 텔레그램 보고 없이 콘솔만
"""
import sys
import os
import importlib
import time
import traceback

# 프로젝트 루트를 path에 추가
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import requests
from utils.secrets_loader import load_secrets

# ── 설정 ─────────────────────────────────────────────

_secrets = load_secrets()
SUPABASE_URL = _secrets["supabase"]["url"]
SUPABASE_SERVICE_KEY = _secrets["supabase"]["service_role_key"]

# 텔레그램 설정 (dev 봇 — Streamlit 외부 실행용)
_tg_dev = _secrets.get("telegram_dev", {})
os.environ.setdefault("TELEGRAM_DEV_BOT_TOKEN", _tg_dev.get("bot_token", ""))
os.environ.setdefault("TELEGRAM_DEV_CHAT_ID", str(_tg_dev.get("chat_id", "")))

TABLES = [
    "users_settings", "clients", "contact_logs",
    "analysis_records", "pioneer_shops", "pioneer_visits",
    "yakwan_records",
]

PAGE_MODULES = [
    "views.page_home",
    "views.page_analysis",
    "views.page_clients",
    "views.page_pioneer_map",
    "views.page_pioneer_route",
    "views.page_stats",
    "views.page_settings",
]

SERVICE_MODULES = [
    "services.analysis_engine",
    "services.excel_generator",
    "services.followup",
    "services.fp_reminder_service",
    "services.remind_trigger",
    "services.yakwan_engine",
    "services.ocr_engine",
    "services.geocoding",
    "services.migration",
    "services.crypto",
    "services.pdf_extractor",
    "services.item_map",
]

UTIL_MODULES = [
    "utils.supabase_client",
    "utils.telegram",
    "utils.helpers",
    "utils.map_utils",
    "utils.db_admin",
]


# ── 테스트 함수 ──────────────────────────────────────

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.details = []

    def ok(self, name):
        self.passed += 1
        self.details.append(f"  ✅ {name}")

    def fail(self, name, reason):
        self.failed += 1
        self.errors.append(f"{name}: {reason}")
        self.details.append(f"  ❌ {name}: {reason}")

    @property
    def total(self):
        return self.passed + self.failed

    @property
    def success(self):
        return self.failed == 0

    def summary(self):
        icon = "✅" if self.success else "❌"
        lines = [f"{icon} *FCPilot 테스트 결과*\n"]
        lines.append(f"통과: {self.passed}/{self.total}")
        if self.errors:
            lines.append(f"\n*실패 항목:*")
            for e in self.errors:
                lines.append(f"  - {e}")
        return "\n".join(lines)

    def detail_report(self):
        return "\n".join(self.details)


def test_supabase_tables(result: TestResult):
    """Supabase 테이블 연결 테스트"""
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }

    for table in TABLES:
        try:
            res = requests.get(
                f"{SUPABASE_URL}/rest/v1/{table}?select=id&limit=0",
                headers=headers, timeout=10,
            )
            if res.status_code == 200:
                result.ok(f"DB: {table}")
            else:
                result.fail(f"DB: {table}", f"HTTP {res.status_code}")
        except Exception as e:
            result.fail(f"DB: {table}", str(e)[:60])


def test_exec_sql_rpc(result: TestResult):
    """exec_sql RPC 함수 테스트"""
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }
    try:
        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
            headers=headers,
            json={"query": "SELECT 1"},
            timeout=10,
        )
        if res.status_code == 200:
            result.ok("DB: exec_sql RPC")
        else:
            result.fail("DB: exec_sql RPC", f"HTTP {res.status_code}")
    except Exception as e:
        result.fail("DB: exec_sql RPC", str(e)[:60])


def test_module_imports(result: TestResult, modules: list[str], category: str):
    """모듈 import 테스트 — 문법 에러/의존성 누락 감지"""
    for mod_name in modules:
        try:
            mod = importlib.import_module(mod_name)
            # render 함수 존재 확인 (pages만)
            if category == "Page" and not hasattr(mod, "render"):
                result.fail(f"{category}: {mod_name}", "render() 없음")
            else:
                result.ok(f"{category}: {mod_name}")
        except Exception as e:
            err = str(e).split("\n")[0][:80]
            result.fail(f"{category}: {mod_name}", err)


def test_config(result: TestResult):
    """config.py 설정값 테스트"""
    try:
        from config import APP_NAME, SESSION_TIMEOUT, CLAUDE_MODEL
        if APP_NAME == "FCPilot":
            result.ok("Config: APP_NAME")
        else:
            result.fail("Config: APP_NAME", f"expected FCPilot, got {APP_NAME}")
        if SESSION_TIMEOUT == 3600:
            result.ok("Config: SESSION_TIMEOUT=60min")
        else:
            result.fail("Config: SESSION_TIMEOUT", f"expected 3600, got {SESSION_TIMEOUT}")
        if "claude" in CLAUDE_MODEL.lower() or "sonnet" in CLAUDE_MODEL.lower():
            result.ok(f"Config: CLAUDE_MODEL")
        else:
            result.fail("Config: CLAUDE_MODEL", CLAUDE_MODEL)
    except Exception as e:
        result.fail("Config", str(e)[:60])


def test_template_exists(result: TestResult):
    """엑셀 템플릿 파일 존재 확인"""
    path = os.path.join(ROOT, "templates", "master_template.xlsx")
    if os.path.exists(path):
        size = os.path.getsize(path)
        if size > 1000:
            result.ok(f"Template: master_template.xlsx ({size:,}B)")
        else:
            result.fail("Template", f"파일 크기 이상: {size}B")
    else:
        result.fail("Template", "master_template.xlsx 없음")


def test_telegram_send(result: TestResult):
    """텔레그램 연결 테스트 (메시지 발송 없이 getMe API로 확인)"""
    try:
        token = os.environ.get("TELEGRAM_DEV_BOT_TOKEN", "")
        res = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=10,
        )
        if res.status_code == 200:
            result.ok("Telegram: 연결")
        else:
            result.fail("Telegram: 연결", f"HTTP {res.status_code}")
    except Exception as e:
        result.fail("Telegram: 연결", str(e)[:60])


def test_streamlit_app_syntax(result: TestResult):
    """app.py 문법 검증"""
    try:
        import py_compile
        py_compile.compile(os.path.join(ROOT, "app.py"), doraise=True)
        result.ok("Syntax: app.py")
    except py_compile.PyCompileError as e:
        result.fail("Syntax: app.py", str(e)[:60])


def test_no_fp_prefix(result: TestResult):
    """fp_ 접두사 잔여 확인 (DB 테이블명/쿠키명 제외)"""
    import glob
    import re
    # DB 테이블명, 쿠키명 등 정당한 fp_ 사용
    allowed = {"fp_reminders", "fp_products", "fp_access", "fp_refresh",
               "fp_reminder_service"}
    allowed_pat = re.compile("|".join(re.escape(a) for a in allowed))
    count = 0
    for pyfile in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True):
        if "tests" in pyfile or "__pycache__" in pyfile:
            continue
        with open(pyfile, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        # allowed 패턴 제거 후 fp_ 잔여 확인
        cleaned = allowed_pat.sub("", content)
        if '"fp_' in cleaned or "'fp_" in cleaned:
            count += 1
    if count == 0:
        result.ok("Code: fp_ 접두사 잔여 0건")
    else:
        result.fail("Code: fp_ 접두사", f"{count}개 파일에 잔여")


# ── 실행 ─────────────────────────────────────────────

def run_all_tests() -> TestResult:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    result = TestResult()

    print("=" * 50)
    print("  FCPilot 자동 테스트")
    print("=" * 50)

    print("\n[1/8] 텔레그램 발송...")
    test_telegram_send(result)

    print("[2/8] Supabase 테이블...")
    test_supabase_tables(result)

    print("[3/8] exec_sql RPC...")
    test_exec_sql_rpc(result)

    print("[4/8] Config 검증...")
    test_config(result)

    print("[5/8] 페이지 모듈 import...")
    test_module_imports(result, PAGE_MODULES, "Page")

    print("[6/8] 서비스/유틸 모듈 import...")
    test_module_imports(result, SERVICE_MODULES, "Service")
    test_module_imports(result, UTIL_MODULES, "Util")

    print("[7/8] 템플릿/문법/코드 검증...")
    test_template_exists(result)
    test_streamlit_app_syntax(result)
    test_no_fp_prefix(result)

    print("[8/8] 완료!")
    print()
    print(result.detail_report())
    print()
    print(f"결과: {result.passed}/{result.total} 통과" +
          (f" ({result.failed} 실패)" if result.failed else ""))

    return result


if __name__ == "__main__":
    result = run_all_tests()
    sys.exit(0 if result.success else 1)
