"""텔레그램 양방향 소통 모듈

송신: Sprint 완료 / 확인 필요 / 경고 알림
수신: getUpdates 폴링 → 명령어 파싱
"""
import os
import time

import requests
import streamlit as st


def _get_config():
    """secrets.toml 또는 환경변수에서 봇 설정 로드"""
    try:
        token = st.secrets["telegram"]["bot_token"]
        chat_id = st.secrets["telegram"]["chat_id"]
    except Exception:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    return token, chat_id


def _api_url():
    token, _ = _get_config()
    return f"https://api.telegram.org/bot{token}"


# ── 송신 ──────────────────────────────────────────────

def send_message(text: str) -> bool:
    """텔레그램 메시지 전송"""
    _, chat_id = _get_config()
    try:
        res = requests.post(
            f"{_api_url()}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        return res.status_code == 200
    except Exception:
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


# ── 수신 (getUpdates 폴링) ────────────────────────────

COMMAND_MAP = {
    "ㅇㅇ": "proceed",
    "진행": "proceed",
    "대기": "wait",
    "잠깐": "wait",
    "상태": "status",
    "중단": "stop",
}


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
    - action: proceed / wait / status / stop / free_text
    """
    cleaned = text.strip().lower()
    action = COMMAND_MAP.get(cleaned, "free_text")
    return {"action": action, "text": text.strip()}


def poll_once(last_offset: int | None = None) -> tuple[dict | None, int | None]:
    """1회 폴링 → (명령 dict | None, 새 offset)

    내 chat_id에서 온 메시지만 처리.
    """
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


def poll_loop(callback, interval: int = 10, max_polls: int = 60):
    """폴링 루프 — callback(command_dict)이 False 반환 시 중단

    Args:
        callback: 명령어 처리 함수. {"action": str, "text": str} 받음.
                  False 반환 시 루프 중단.
        interval: 폴링 간격 (초)
        max_polls: 최대 폴링 횟수 (무한루프 방지)
    """
    offset = None
    # 기존 메시지 스킵 — 현재 offset 확보
    updates = get_updates(offset=None, timeout=1)
    if updates:
        offset = updates[-1]["update_id"] + 1

    for _ in range(max_polls):
        cmd, offset = poll_once(offset)
        if cmd is not None:
            result = callback(cmd)
            if result is False:
                break
        time.sleep(interval)
