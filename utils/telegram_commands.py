"""텔레그램 명령 수신/처리 (telegram.py에서 분리)"""
import time
from datetime import datetime

import requests

from utils.telegram import _get_config, send_message, report_status, ack_instruction

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
