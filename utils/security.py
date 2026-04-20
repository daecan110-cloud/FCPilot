"""보안 미들웨어 — 로그인 brute force 차단 + 입력 검증 + 경로 검증"""
import re
import time
import logging

import streamlit as st


# ── 로그인 시도 제한 ─────────────────────────────────────

# {ip_or_email: [timestamp, timestamp, ...]}
_login_attempts: dict[str, list[float]] = {}
_MAX_ATTEMPTS = 5       # 5회 이내
_WINDOW_SECONDS = 300   # 5분 윈도우
_LOCKOUT_SECONDS = 600  # 초과 시 10분 잠금


def check_login_throttle(email: str) -> str | None:
    """로그인 시도 전 호출. 차단 시 에러 메시지 반환, 통과 시 None."""
    key = email.lower().strip()
    now = time.time()
    attempts = _login_attempts.get(key, [])

    # 윈도우 밖 기록 제거
    attempts = [t for t in attempts if now - t < _LOCKOUT_SECONDS]
    _login_attempts[key] = attempts

    if len(attempts) >= _MAX_ATTEMPTS:
        oldest = min(attempts[-_MAX_ATTEMPTS:])
        remaining = int(_LOCKOUT_SECONDS - (now - oldest))
        if remaining > 0:
            logging.warning("로그인 시도 초과: %s (%d회)", key[:3] + "***", len(attempts))
            return f"로그인 시도가 너무 많습니다. {remaining}초 후 다시 시도해주세요."
    return None


def record_login_attempt(email: str):
    """로그인 실패 시 호출."""
    key = email.lower().strip()
    _login_attempts.setdefault(key, []).append(time.time())


def clear_login_attempts(email: str):
    """로그인 성공 시 호출."""
    key = email.lower().strip()
    _login_attempts.pop(key, None)


# ── 입력 검증 ────────────────────────────────────────────

# SQL injection / Supabase filter 조작 시도 패턴
_DANGEROUS_PATTERNS = re.compile(
    r"(--|;|'|\"|\bOR\b\s+\b1\b\s*=\s*\b1\b|\bUNION\b|\bDROP\b|\bDELETE\b"
    r"|\bINSERT\b|\bUPDATE\b|\bEXEC\b|\bEXECUTE\b|\bALTER\b"
    r"|<script|javascript:|on\w+=)",
    re.IGNORECASE,
)


def sanitize_search_input(text: str) -> str:
    """검색 입력에서 위험 패턴 제거. 안전한 문자열 반환."""
    if not text:
        return ""
    cleaned = text.strip()
    if _DANGEROUS_PATTERNS.search(cleaned):
        logging.warning("위험 입력 감지 및 차단: %s", cleaned[:30])
        # 위험 패턴 제거 후 안전한 부분만 반환
        cleaned = _DANGEROUS_PATTERNS.sub("", cleaned).strip()
    # 길이 제한
    return cleaned[:200]


def validate_uuid(value: str) -> bool:
    """UUID 형식 검증 (client_id, fc_id 등)"""
    if not value:
        return False
    return bool(re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        value.lower(),
    ))


# ── Storage 경로 검증 ────────────────────────────────────

def validate_storage_path(path: str, fc_id: str) -> bool:
    """Storage 경로가 현재 사용자 소유인지 검증.
    path traversal (../) 공격 및 타 사용자 파일 접근 차단.
    """
    if not path or not fc_id:
        return False
    # path traversal 차단
    if ".." in path or path.startswith("/"):
        logging.warning("경로 조작 시도 차단: %s", path[:50])
        return False
    # fc_id 소속 확인
    if not path.startswith(f"{fc_id}/"):
        logging.warning("타 사용자 파일 접근 시도 차단: %s (fc: %s)", path[:50], fc_id[:8])
        return False
    return True
