"""텔레그램 봇 모듈 — 개발 알림(dev) / 사용자 기능(user) 분리

dev 봇 (claudeFC_bot): Sprint 완료, 에러, 테스트, 커밋 알림
user 봇 (FCPilot): 리마인드, 고객 조회/등록, Claude 챗
"""
import os

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


# ── 명령 수신/처리는 utils/telegram_commands.py로 분리 ──
