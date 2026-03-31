"""FCPilot 설정 및 클라이언트 초기화"""
import streamlit as st

# 앱 정보
APP_NAME = "FCPilot"
APP_VERSION = "1.0.0"

# 페이지 설정
PAGE_CONFIG = {
    "page_title": "FCPilot - 보험 FC 업무 플랫폼",
    "page_icon": "🛡️",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# 파일 업로드 제한
ALLOWED_FILE_TYPES = ["pdf", "jpg", "jpeg", "png"]
MAX_FILE_SIZE_MB = 10

# 세션 타임아웃 (초)
SESSION_TIMEOUT = 60 * 60  # 60분

# Claude API 설정
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS = 4096
