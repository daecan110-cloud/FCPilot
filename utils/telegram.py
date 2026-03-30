"""텔레그램 알림 모듈

CLAUDE.md 규칙: 정확히 3가지만 알림
- ✅ Sprint 완료
- 🔧 영민 직접 확인 필요 (+ ⏳ waiting 메시지)
- ⚠️ Opus 전환 필요
"""
import requests

BOT_TOKEN = "8415171186:AAFks4TDdB4MSRapeMnE5CnXm6QC26r6BXs"
CHAT_ID = "8201988543"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(text: str) -> bool:
    """텔레그램 메시지 전송"""
    try:
        res = requests.post(
            f"{API_URL}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        return res.status_code == 200
    except Exception:
        return False


def notify_sprint_complete(sprint: str, summary: str):
    """Sprint 완료 알림"""
    send_message(f"✅ *{sprint} 완료*\n\n{summary}")


def notify_action_needed(message: str):
    """영민 확인 필요 알림"""
    send_message(f"🔧 *확인 필요*\n\n{message}\n\n⏳ 대기 중...")


def notify_warning(message: str):
    """경고 알림"""
    send_message(f"⚠️ *알림*\n\n{message}")
