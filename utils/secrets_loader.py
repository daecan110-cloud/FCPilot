"""Streamlit 외부 스크립트용 secrets.toml 로더

Streamlit 앱은 st.secrets를 사용하지만, CLI 스크립트(test_all.py,
command_poller.py 등)는 st.secrets를 쓸 수 없다.
이 모듈이 secrets.toml을 직접 파싱하여 동일한 설정을 제공한다.

사용법:
    from utils.secrets_loader import load_secrets
    secrets = load_secrets()
    url = secrets["supabase"]["url"]
"""
import os
import tomllib
from pathlib import Path


def load_secrets() -> dict:
    """secrets.toml을 파싱하여 dict로 반환.

    탐색 순서:
    1. .streamlit/secrets.toml (프로젝트 루트 기준)
    2. 환경변수 폴백 (최소한의 키만)
    """
    root = Path(__file__).parent.parent
    secrets_path = root / ".streamlit" / "secrets.toml"

    if secrets_path.exists():
        with open(secrets_path, "rb") as f:
            return tomllib.load(f)

    # secrets.toml 없으면 환경변수에서 최소 설정 구성
    return {
        "supabase": {
            "url": os.environ.get("SUPABASE_URL", ""),
            "anon_key": os.environ.get("SUPABASE_ANON_KEY", ""),
            "service_role_key": os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
        },
        "telegram_dev": {
            "bot_token": os.environ.get("TELEGRAM_DEV_BOT_TOKEN", ""),
            "chat_id": os.environ.get("TELEGRAM_DEV_CHAT_ID", ""),
        },
        "telegram_user": {
            "bot_token": os.environ.get("TELEGRAM_USER_BOT_TOKEN", ""),
            "chat_id": os.environ.get("TELEGRAM_USER_CHAT_ID", ""),
        },
    }
