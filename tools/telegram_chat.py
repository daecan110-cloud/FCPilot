"""텔레그램 ↔ Claude 양방향 챗봇

PC에서 실행하면 텔레그램으로 Claude와 대화 가능.
사용법: python -u tools/telegram_chat.py
"""
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# stdout 버퍼링 해제
sys.stdout.reconfigure(line_buffering=True)

import anthropic
import requests

# 프로젝트 루트를 path에 추가
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from utils.secrets_loader import load_secrets

# ── 설정 로드 ────────────────────────────────────────

def load_config() -> dict:
    """secrets.toml에서 설정 로드 (telegram_chat 섹션 = 대화용 봇)"""
    secrets = load_secrets()
    chat_cfg = secrets.get("telegram_chat", {})
    return {
        "bot_token": chat_cfg.get("bot_token", "")
            or os.environ.get("TELEGRAM_CHAT_BOT_TOKEN", ""),
        "chat_id": str(secrets.get("telegram", {}).get("chat_id", ""))
            or os.environ.get("TELEGRAM_CHAT_ID", ""),
        "claude_api_key": secrets.get("claude", {}).get("api_key", "")
            or os.environ.get("ANTHROPIC_API_KEY", ""),
    }


CONFIG = load_config()
BOT_TOKEN = CONFIG["bot_token"]
CHAT_ID = CONFIG["chat_id"]
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── Claude 클라이언트 ────────────────────────────────

client = anthropic.Anthropic(api_key=CONFIG["claude_api_key"])

SYSTEM_PROMPT = """너는 FCPilot 어시스턴트야. 보험 FC 영민의 업무를 돕는 AI 비서.
텔레그램으로 간단한 질문에 답변하고, 업무 관련 도움을 줘.
답변은 짧고 핵심만. 한국어로 대답해."""

# 대화 히스토리 (메모리)
conversation: list[dict] = []
MAX_HISTORY = 20


# ── 텔레그램 API ─────────────────────────────────────

def send_message(chat_id: str, text: str) -> bool:
    """텔레그램 메시지 전송"""
    url = f"{API_BASE}/sendMessage"
    # 4096자 제한 처리
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        try:
            res = requests.post(
                url,
                json={"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"},
                timeout=10,
            )
            if res.status_code == 400:
                # Markdown 파싱 실패 시 plain text
                requests.post(
                    url,
                    json={"chat_id": chat_id, "text": chunk},
                    timeout=10,
                )
        except Exception as e:
            print(f"[전송 실패] {e}")
            return False
    return True


def get_updates(offset: int | None = None) -> list[dict]:
    """새 메시지 가져오기"""
    params = {"timeout": 30, "allowed_updates": ["message"]}
    if offset is not None:
        params["offset"] = offset
    try:
        res = requests.get(
            f"{API_BASE}/getUpdates",
            params=params,
            timeout=35,
        )
        if res.status_code == 200:
            return res.json().get("result", [])
    except Exception as e:
        print(f"[폴링 오류] {e}")
    return []


# ── Claude 호출 ──────────────────────────────────────

def ask_claude(user_msg: str) -> str:
    """Claude API로 답변 생성"""
    conversation.append({"role": "user", "content": user_msg})

    # 히스토리 제한
    if len(conversation) > MAX_HISTORY:
        conversation[:] = conversation[-MAX_HISTORY:]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=conversation,
        )
        reply = response.content[0].text
        conversation.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"Claude API 오류: {e}"


# ── 명령어 처리 ──────────────────────────────────────

def handle_command(text: str) -> str | None:
    """특수 명령어 처리. None이면 일반 대화로 넘김."""
    cmd = text.strip().lower()
    if cmd == "/start":
        return "FCPilot 챗봇 시작! 질문을 보내세요."
    if cmd == "/clear":
        conversation.clear()
        return "대화 히스토리 초기화 완료."
    if cmd == "/help":
        return (
            "*FCPilot 텔레그램 봇*\n\n"
            "그냥 메시지를 보내면 Claude가 답변합니다.\n\n"
            "*명령어:*\n"
            "/clear — 대화 초기화\n"
            "/help — 도움말"
        )
    return None


# ── 메인 루프 ────────────────────────────────────────

def main():
    print("=" * 50)
    print("FCPilot 텔레그램 챗봇 시작")
    print(f"Chat ID: {CHAT_ID}")
    print("종료: Ctrl+C")
    print("=" * 50)

    if not BOT_TOKEN or not CHAT_ID:
        print("[오류] bot_token 또는 chat_id 없음. secrets.toml 확인.")
        sys.exit(1)

    if not CONFIG["claude_api_key"]:
        print("[오류] Claude API 키 없음. secrets.toml 확인.")
        sys.exit(1)

    # 기존 메시지 스킵
    updates = get_updates()
    offset = updates[-1]["update_id"] + 1 if updates else None
    print("[준비 완료] 메시지 대기 중...\n")

    send_message(CHAT_ID, "FCPilot 봇이 시작됐습니다. 질문을 보내세요!")

    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "")

                # 내 채팅만 처리
                if chat_id != CHAT_ID or not text:
                    continue

                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] 영민: {text}")

                # 명령어 확인
                cmd_reply = handle_command(text)
                if cmd_reply:
                    send_message(chat_id, cmd_reply)
                    print(f"[{ts}] 봇: {cmd_reply[:50]}...")
                    continue

                # Claude 호출
                send_message(chat_id, "생각 중...")
                reply = ask_claude(text)
                send_message(chat_id, reply)
                print(f"[{ts}] 봇: {reply[:80]}...")

        except KeyboardInterrupt:
            print("\n봇 종료.")
            send_message(CHAT_ID, "FCPilot 봇이 종료됩니다.")
            break
        except Exception as e:
            print(f"[오류] {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
