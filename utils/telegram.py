"""텔레그램 양방향 소통 모듈

송신: Sprint 완료 / 확인 필요 / 경고 / 상태 보고
수신: getUpdates 폴링 → 명령어 파싱 + 자유 텍스트 지시
"""
import os
import time
from datetime import datetime

import requests
import streamlit as st


def _get_config():
    """secrets.toml 또는 환경변수에서 봇 설정 로드"""
    try:
        token = st.secrets["telegram"]["bot_token"]
        chat_id = st.secrets["telegram"]["chat_id"]
        return token, chat_id
    except Exception:
        pass

    # CLI 환경: secrets.toml 직접 파싱
    try:
        import tomllib
        from pathlib import Path
        secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
        with open(secrets_path, "rb") as f:
            data = tomllib.load(f)
        token = data["telegram"]["bot_token"]
        chat_id = data["telegram"]["chat_id"]
        return token, chat_id
    except Exception:
        pass

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    return token, chat_id


def _api_url():
    token, _ = _get_config()
    return f"https://api.telegram.org/bot{token}"


# ── 송신 ──────────────────────────────────────────────

def send_message(text: str) -> bool:
    """텔레그램 메시지 전송"""
    token, chat_id = _get_config()
    if not token or not chat_id:
        print("[TELEGRAM] FAIL: token or chat_id missing")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        res = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        if res.status_code == 200:
            print(f"[TELEGRAM] OK: {res.status_code}")
            return True
        # Markdown 파싱 오류 시 plain text 재시도
        if res.status_code == 400:
            res2 = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
            if res2.status_code == 200:
                print(f"[TELEGRAM] OK (plain text): {res2.status_code}")
                return True
            print(f"[TELEGRAM] FAIL: {res2.status_code} {res2.text[:200]}")
            return False
        print(f"[TELEGRAM] FAIL: {res.status_code} {res.text[:200]}")
        return False
    except Exception as e:
        print(f"[TELEGRAM] FAIL: {e}")
        return False


def notify_sprint_complete(sprint: str, summary: str):
    send_message(f"✅ *{sprint} 완료*\n\n{summary}")


def notify_action_needed(message: str):
    send_message(f"🔧 *확인 필요*\n\n{message}\n\n⏳ 대기 중...")


def notify_warning(message: str):
    send_message(f"⚠️ *알림*\n\n{message}")


def notify_reminder(reminders: list[dict]):
    """리마인드 대상 알림 발송"""
    if not reminders:
        return
    lines = ["📋 *오늘의 리마인드*\n"]
    for r in reminders:
        name = r.get("client_name", r.get("shop_name", ""))
        action = r.get("action", r.get("memo", ""))
        overdue = "🔴" if r.get("overdue") else "🟡"
        lines.append(f"{overdue} {name} — {action}")
    send_message("\n".join(lines))


def report_status(status_text: str):
    """현재 상태를 텔레그램으로 보고"""
    send_message(f"📊 *현재 상태*\n\n{status_text}")


def ack_instruction(text: str):
    """자유 텍스트 지시 수신 확인"""
    send_message(f"📩 *지시 수신*\n\n\"{text}\"\n\n🔄 처리 중...")


def report_result(instruction: str, result: str):
    """자유 텍스트 지시 처리 결과 보고"""
    send_message(f"✅ *처리 완료*\n\n📩 {instruction}\n\n{result}")


# ── 수신 (getUpdates 폴링) ────────────────────────────

COMMAND_MAP = {
    "ㅇㅇ": "proceed",
    "진행": "proceed",
    "대기": "wait",
    "잠깐": "wait",
    "상태": "status",
    "중단": "stop",
}

# 모듈 레벨 offset — 세션 동안 유지
_last_offset: int | None = None
_pending_instructions: list[dict] = []


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
    """메시지 텍스트 → 명령어 파싱

    Returns: {"action": str, "text": str}
    - action: proceed / wait / status / stop / instruction
    """
    cleaned = text.strip()
    action = COMMAND_MAP.get(cleaned.lower(), "instruction")
    return {"action": action, "text": cleaned}


def skip_old_messages():
    """기존 메시지 스킵 — 세션 시작 시 호출"""
    global _last_offset
    updates = get_updates(offset=None, timeout=1)
    if updates:
        _last_offset = updates[-1]["update_id"] + 1


def poll_once(last_offset: int | None = None) -> tuple[dict | None, int | None]:
    """1회 폴링 → (명령 dict | None, 새 offset)"""
    _, my_chat_id = _get_config()
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
    """새 명령어/지시 확인 — 작업 사이에 호출

    Returns: 새 명령어 리스트. 빈 리스트면 새 메시지 없음.
    각 항목: {"action": str, "text": str, "timestamp": str}
    """
    global _last_offset
    _, my_chat_id = _get_config()
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
    """미처리 자유 텍스트 지시 목록 반환 후 비움"""
    global _pending_instructions
    pending = _pending_instructions.copy()
    _pending_instructions.clear()
    return pending


def process_commands(commands: list[dict], status_text: str = "") -> str | None:
    """명령어 리스트 처리 — 자동 응답 포함

    Returns:
        None: 계속 진행
        "wait": 대기 요청
        "stop": 중단 요청
        "proceed": 다음 단계 진행
    """
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
    """폴링 루프 — callback(command_dict)이 False 반환 시 중단"""
    skip_old_messages()

    for _ in range(max_polls):
        cmd, _offset_unused = poll_once(_last_offset)
        if cmd is not None:
            result = callback(cmd)
            if result is False:
                break
        time.sleep(interval)
