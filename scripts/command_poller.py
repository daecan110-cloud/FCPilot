"""command_queue 폴링 스크립트 — 로컬에서 실행

텔레그램 → Edge Function → command_queue에 저장된 명령을
폴링하여 읽고, 실행 결과를 텔레그램으로 보고한다.

사용법:
  python scripts/command_poller.py          # 폴링 시작 (10초 간격)
  python scripts/command_poller.py --once   # 1회만 실행
"""
import os
import sys
import time
import subprocess

# 프로젝트 루트를 path에 추가
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import requests
from utils.secrets_loader import load_secrets

# ── 설정 ─────────────────────────────────────────────

_secrets = load_secrets()
SUPABASE_URL = _secrets["supabase"]["url"]
SUPABASE_SERVICE_KEY = _secrets["supabase"]["service_role_key"]

_tg_dev = _secrets.get("telegram_dev", {})
os.environ.setdefault("TELEGRAM_DEV_BOT_TOKEN", _tg_dev.get("bot_token", ""))
os.environ.setdefault("TELEGRAM_DEV_CHAT_ID", str(_tg_dev.get("chat_id", "")))

HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

POLL_INTERVAL = 10  # 초


# ── Supabase 쿼리 ───────────────────────────────────

def fetch_pending_commands() -> list[dict]:
    """pending 상태 명령 조회"""
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/command_queue"
        "?status=eq.pending&order=created_at.asc&limit=5",
        headers=HEADERS, timeout=10,
    )
    if res.status_code == 200:
        return res.json()
    return []


def update_command(cmd_id: str, status: str, result: str = ""):
    """명령 상태 업데이트"""
    body: dict = {"status": status}
    if result:
        body["result"] = result[:500]
    if status in ("completed", "failed"):
        body["completed_at"] = "now()"

    requests.patch(
        f"{SUPABASE_URL}/rest/v1/command_queue?id=eq.{cmd_id}",
        headers=HEADERS, json=body, timeout=10,
    )


# ── 명령 실행 ────────────────────────────────────────

SAFE_COMMANDS = {
    "테스트": f"python {os.path.join(ROOT, 'tests', 'test_all.py')} --quiet",
    "테스트해줘": f"python {os.path.join(ROOT, 'tests', 'test_all.py')} --quiet",
    "git status": "git status",
    "git pull": "git pull origin main",
    "git push": "git push origin main",
}


def execute_command(command: str) -> tuple[bool, str]:
    """명령어 실행 → (성공여부, 결과 텍스트)"""
    cmd_lower = command.strip().lower()

    # 안전한 명령어 매핑
    shell_cmd = SAFE_COMMANDS.get(cmd_lower)

    if not shell_cmd:
        # git 명령어 허용
        if cmd_lower.startswith("git "):
            shell_cmd = command
        else:
            return False, f"미지원 명령: {command}"

    try:
        result = subprocess.run(
            shell_cmd, shell=True, capture_output=True,
            text=True, timeout=60, cwd=ROOT,
        )
        output = (result.stdout or "") + (result.stderr or "")
        output = output.strip()[:400]
        success = result.returncode == 0
        return success, output or ("성공" if success else "실패")
    except subprocess.TimeoutExpired:
        return False, "타임아웃 (60초 초과)"
    except Exception as e:
        return False, str(e)[:200]


# ── 텔레그램 보고 ────────────────────────────────────

def send_telegram(text: str):
    """결과 텔레그램 발송 (dev 봇)"""
    token = os.environ.get("TELEGRAM_DEV_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_DEV_CHAT_ID", "")
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception:
        pass


# ── 메인 루프 ────────────────────────────────────────

def process_once() -> int:
    """1회 폴링 → 명령 실행. 처리 건수 반환."""
    commands = fetch_pending_commands()
    if not commands:
        return 0

    for cmd in commands:
        cmd_id = cmd["id"]
        command = cmd["command"]

        # processing 상태로 변경
        update_command(cmd_id, "processing")

        # 실행
        success, result = execute_command(command)
        status = "completed" if success else "failed"
        update_command(cmd_id, status, result)

        # 텔레그램 보고
        icon = "✅" if success else "❌"
        send_telegram(f"{icon} *명령 실행 완료*\n\n📩 {command}\n\n{result}")

    return len(commands)


def main():
    once = "--once" in sys.argv
    print(f"FCPilot command_poller {'(1회 모드)' if once else '시작'}")
    print(f"  Polling interval: {POLL_INTERVAL}s")
    print(f"  Project root: {ROOT}")
    print()

    if once:
        n = process_once()
        print(f"처리: {n}건")
        return

    send_telegram("🟢 *command\\_poller 시작*\n\nPC에서 명령 대기 중...")

    try:
        while True:
            n = process_once()
            if n > 0:
                print(f"[{time.strftime('%H:%M:%S')}] {n}건 처리")
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n종료")
        send_telegram("🔴 *command\\_poller 종료*")


if __name__ == "__main__":
    main()
