"""텔레그램 봇 모듈 — 개발 알림(dev) / 사용자 기능(user) 분리

dev 봇 (claudeFC_bot): Sprint 완료, 에러, 테스트, 커밋 알림
user 봇 (FCPilot): 리마인드, 고객 조회/등록, Claude 챗
"""
import os
import time
from datetime import datetime

import requests


# ── 설정 로드 ────────────────────────────────────────────

def _get_config(bot: str = "dev"):
    """secrets.toml 또는 환경변수에서 봇 설정 로드

    Args:
        bot: "dev" (작업 알림) 또는 "user" (사용자 기능)
    """
    section = "telegram_dev" if bot == "dev" else "telegram_user"
    env_prefix = "TELEGRAM_DEV" if bot == "dev" else "TELEGRAM_USER"

    # Streamlit 앱 환경
    try:
        import streamlit as st
        token = st.secrets[section]["bot_token"]
        chat_id = st.secrets[section]["chat_id"]
        return token, chat_id
    except Exception:
        pass

    # CLI 환경: secrets.toml 직접 파싱
    try:
        from utils.secrets_loader import load_secrets
        data = load_secrets()
        token = data[section]["bot_token"]
        chat_id = data[section]["chat_id"]
        return token, chat_id
    except Exception:
        pass

    token = os.environ.get(f"{env_prefix}_BOT_TOKEN", "")
    chat_id = os.environ.get(f"{env_prefix}_CHAT_ID", "")
    return token, chat_id


# ── 공통 전송 ────────────────────────────────────────────

def _send(text: str, bot: str = "dev") -> bool:
    """텔레그램 메시지 전송 (내부용)"""
    token, chat_id = _get_config(bot)
    if not token or not chat_id:
        print(f"[TELEGRAM-{bot}] FAIL: token or chat_id missing")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        res = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        if res.status_code == 200:
            return True
        # Markdown 파싱 오류 시 plain text 재시도
        if res.status_code == 400:
            res2 = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
            return res2.status_code == 200
        return False
    except Exception as e:
        print(f"[TELEGRAM-{bot}] FAIL: {e}")
        return False


# ── 개발 알림 (claudeFC_bot) ─────────────────────────────

def send_message(text: str) -> bool:
    """개발 알림 메시지 전송 (하위 호환)"""
    return _send(text, bot="dev")


def notify_sprint_complete(sprint: str, summary: str):
    _send(f"✅ *{sprint} 완료*\n\n{summary}", bot="dev")


def notify_action_needed(message: str):
    _send(f"🔧 *확인 필요*\n\n{message}\n\n⏳ 대기 중...", bot="dev")


def notify_warning(message: str):
    _send(f"⚠️ *알림*\n\n{message}", bot="dev")


def report_status(status_text: str):
    _send(f"📊 *현재 상태*\n\n{status_text}", bot="dev")


def ack_instruction(text: str):
    _send(f"📩 *지시 수신*\n\n\"{text}\"\n\n🔄 처리 중...", bot="dev")


def report_result(instruction: str, result: str):
    _send(f"✅ *처리 완료*\n\n📩 {instruction}\n\n{result}", bot="dev")


# ── 사용자 알림 (FCPilot 봇) ─────────────────────────────

def send_user_message(text: str) -> bool:
    """사용자 봇으로 메시지 전송"""
    return _send(text, bot="user")


def notify_reminder(reminders: list[dict], pioneers: list[dict] | None = None):
    """리마인드 대상 알림 발송 → 사용자 봇"""
    from datetime import date as _date
    today_str = str(_date.today())
    lines = [f"📋 *오늘의 리마인드* ({_date.today().strftime('%m/%d')})\n"]

    if reminders:
        lines.append("*💬 상담 리마인드*")
        for r in reminders:
            client = r.get("clients") or {}
            name = client.get("name", "이름 없음")
            grade = client.get("prospect_grade", "")
            purpose = r.get("purpose", "")
            d = r.get("reminder_date", "")
            badge = "🔴" if d < today_str else "🟡"
            grade_str = f" [{grade}]" if grade else ""
            lines.append(f"{badge} {name}{grade_str} — {purpose} ({d})")

    if pioneers:
        if reminders:
            lines.append("")
        lines.append("*🗺️ 개척 팔로업*")
        for p in pioneers:
            shop_name = (p.get("shop") or {}).get("shop_name", "매장명 없음")
            action = p.get("action", "팔로업")
            lines.append(f"🔴 {shop_name} — {action}")

    _send("\n".join(lines), bot="user")


# ── 수신 (getUpdates 폴링) — dev 봇 ─────────────────────

COMMAND_MAP = {
    "ㅇㅇ": "proceed",
    "진행": "proceed",
    "대기": "wait",
    "잠깐": "wait",
    "상태": "status",
    "중단": "stop",
}

_last_offset: int | None = None
_pending_instructions: list[dict] = []


def _api_url():
    token, _ = _get_config("dev")
    return f"https://api.telegram.org/bot{token}"


def get_updates(offset: int | None = None, timeout: int = 5) -> list[dict]:
    """getUpdates API 호출"""
    params = {"timeout": timeout, "allowed_updates": ["message"]}
    if offset is not None:
        params["offset"] = offset
    try:
        res = requests.get(
            f"{_api_url()}/getUpdates",
            params=params,
            timeout=timeout + 5,
        )
        if res.status_code == 200:
            return res.json().get("result", [])
    except Exception:
        pass
    return []


def parse_command(text: str) -> dict:
    cleaned = text.strip()
    action = COMMAND_MAP.get(cleaned.lower(), "instruction")
    return {"action": action, "text": cleaned}


def skip_old_messages():
    global _last_offset
    updates = get_updates(offset=None, timeout=1)
    if updates:
        _last_offset = updates[-1]["update_id"] + 1


def poll_once(last_offset: int | None = None) -> tuple[dict | None, int | None]:
    _, my_chat_id = _get_config("dev")
    updates = get_updates(offset=last_offset, timeout=3)
    if not updates:
        return None, last_offset

    latest = updates[-1]
    new_offset = latest["update_id"] + 1

    msg = latest.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = msg.get("text", "")

    if chat_id != str(my_chat_id) or not text:
        return None, new_offset

    return parse_command(text), new_offset


def check_for_commands() -> list[dict]:
    global _last_offset
    _, my_chat_id = _get_config("dev")
    updates = get_updates(offset=_last_offset, timeout=1)
    if not updates:
        return []

    commands = []
    for u in updates:
        _last_offset = u["update_id"] + 1
        msg = u.get("message", {})
        chat_id = str(msg.get("chat", {}).get("id", ""))
        text = msg.get("text", "")
        ts = msg.get("date", 0)

        if chat_id != str(my_chat_id) or not text:
            continue

        cmd = parse_command(text)
        cmd["timestamp"] = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
        commands.append(cmd)

    return commands


def get_pending_instructions() -> list[dict]:
    global _pending_instructions
    pending = _pending_instructions.copy()
    _pending_instructions.clear()
    return pending


def process_commands(commands: list[dict], status_text: str = "") -> str | None:
    global _pending_instructions
    result = None

    for cmd in commands:
        action = cmd["action"]
        text = cmd["text"]

        if action == "status":
            report_status(status_text or "작업 진행 중")
        elif action == "wait":
            send_message("⏸️ *대기*\n\n작업을 일시 중단합니다.\n\"진행\" 또는 \"ㅇㅇ\"으로 재개하세요.")
            result = "wait"
        elif action == "stop":
            send_message("🛑 *중단*\n\n현재 작업을 중단합니다.")
            result = "stop"
        elif action == "proceed":
            send_message("▶️ *진행*\n\n다음 단계로 진행합니다.")
            result = "proceed"
        elif action == "instruction":
            ack_instruction(text)
            _pending_instructions.append(cmd)

    return result


def poll_loop(callback, interval: int = 10, max_polls: int = 60):
    skip_old_messages()
    for _ in range(max_polls):
        cmd, _offset_unused = poll_once(_last_offset)
        if cmd is not None:
            result = callback(cmd)
            if result is False:
                break
        time.sleep(interval)
