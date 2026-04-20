"""FCPilot 설정 및 클라이언트 초기화"""
import streamlit as st

# 앱 정보
APP_NAME = "FCPilot"

# 페이지 설정
PAGE_CONFIG = {
    "page_title": "FCPilot - 보험 FC 업무 플랫폼",
    "page_icon": "🛡️",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# 파일 업로드 제한
MAX_FILE_SIZE_MB = 10

# 세션 타임아웃 (초)
SESSION_TIMEOUT = 60 * 60  # 60분

# 유입경로 기본 카테고리 (단일 소스)
DEFAULT_SOURCE_CATEGORIES = ["DB고객", "지인", "개척", "소개", "기타"]

# 연락 방식
TOUCH_OPTIONS = ["콜", "방문", "문자", "이메일", "기타"]

# 개척 업종
CATEGORY_OPTIONS = [
    "음식점", "카페", "미용실/뷰티", "학원/교육", "병원/약국",
    "편의점/마트", "의류/패션", "사무실/오피스",
    "골프용품샵", "골프웨어샵", "중고골프샵", "골프 수리/피팅",
    "종합 골프샵", "스크린골프",
    "기타",
]

# 보험 상품 카테고리
INSURANCE_CATEGORIES = ["종신보험", "건강보험", "연금보험", "저축보험", "변액보험", "기타"]
INSURANCE_CAT_ICON = {
    "종신보험": "🔵", "건강보험": "🟢", "연금보험": "🟡",
    "저축보험": "🟠", "변액보험": "🟣", "기타": "⚪",
}

# Claude API 설정
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS = 4096
