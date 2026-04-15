"""FCPilot 인증 모듈 — Supabase Auth + 쿠키 기반 세션 유지"""
import time
import streamlit as st
from utils.supabase_client import get_supabase_client
from config import SESSION_TIMEOUT

_COOKIE_ACCESS = "fp_access"
_COOKIE_REFRESH = "fp_refresh"
_COOKIE_MAX_AGE = 30 * 24 * 3600  # 30일


def _ctrl():
    """CookieController 인스턴스 (key 고정으로 동일 컴포넌트 재사용)"""
    try:
        from streamlit_cookies_controller import CookieController
        return CookieController(key="fcpilot_cookies")
    except Exception:
        return None


# ── 세션 초기화 ──────────────────────────────────────────

def init_auth():
    """앱 최상단 호출:
    1. 로그인 직후 pending 쿠키 저장
    2. 새로고침 시 쿠키에서 Supabase 세션 복원
    """
    # 1. 이미 로그인됨 — pending 쿠키가 있으면 이번 렌더에서 저장
    if st.session_state.get("user"):
        pending = st.session_state.pop("_pending_cookies", None)
        if pending:
            ctrl = _ctrl()
            if ctrl:
                try:
                    ctrl.set(_COOKIE_ACCESS, pending["access"], max_age=_COOKIE_MAX_AGE)
                    ctrl.set(_COOKIE_REFRESH, pending["refresh"], max_age=_COOKIE_MAX_AGE)
                except Exception:
                    pass
        return

    # 2. 세션 없음 — 쿠키에서 복원 시도
    ctrl = _ctrl()
    if ctrl is None:
        return

    try:
        access = ctrl.get(_COOKIE_ACCESS)
        refresh = ctrl.get(_COOKIE_REFRESH)
    except Exception:
        return

    if not access or not refresh:
        return

    try:
        sb = get_supabase_client()
        res = sb.auth.set_session(access, refresh)
        if res and res.user:
            st.session_state.user = res.user
            st.session_state.session = res.session
            st.session_state.last_activity = time.time()
            st.rerun()
    except Exception:
        # 토큰 만료 — 쿠키 삭제
        try:
            ctrl.remove(_COOKIE_ACCESS)
            ctrl.remove(_COOKIE_REFRESH)
        except Exception:
            pass


# ── 상태 확인 ─────────────────────────────────────────────

def is_logged_in() -> bool:
    return st.session_state.get("user") is not None


def get_current_user_id() -> str:
    user = st.session_state.get("user")
    return user.id if user else ""


def get_current_user_email() -> str:
    user = st.session_state.get("user")
    return user.email if user else ""


# Claude API 사용 허용 이메일
_ADMIN_EMAILS = {"japanstudy1205@gmail.com"}


def is_api_allowed() -> bool:
    """Claude API 기능 사용 가능 여부 (관리자 이메일만 허용)"""
    return get_current_user_email() in _ADMIN_EMAILS


def get_user_status() -> str:
    """users_settings.status 반환 — session_state 캐싱으로 매 렌더 DB 조회 방지"""
    if "cached_user_status" in st.session_state:
        return st.session_state.cached_user_status
    user_id = get_current_user_id()
    if not user_id:
        return "anonymous"
    try:
        sb = get_supabase_client()
        res = sb.table("users_settings").select("status, role").eq("id", user_id).execute()
        if res.data:
            row = res.data[0]
            status = row.get("status") or "approved"
            # role도 함께 캐싱해서 is_admin() 추가 조회 방지
            st.session_state.cached_user_status = status
            st.session_state.cached_user_role = row.get("role", "user")
            return status
        st.session_state.cached_user_status = "pending"
        return "pending"
    except Exception:
        pass
    return "approved"


def is_admin() -> bool:
    if "cached_user_role" not in st.session_state:
        get_user_status()  # 한 번 호출로 role까지 캐싱
    return st.session_state.get("cached_user_role") == "admin"


def check_session_timeout():
    """60분 무활동 시 자동 로그아웃"""
    if "last_activity" not in st.session_state:
        st.session_state.last_activity = time.time()
        return
    elapsed = time.time() - st.session_state.last_activity
    if elapsed > SESSION_TIMEOUT:
        st.session_state._timeout_msg = True
        logout()
        st.rerun()
    else:
        st.session_state.last_activity = time.time()


# ── 로그인 UI ─────────────────────────────────────────────

def show_login_page():
    if st.session_state.pop("_timeout_msg", False):
        st.warning("60분 동안 활동이 없어 자동 로그아웃되었습니다.")
    st.title("🛡️ FCPilot")
    st.caption("보험 FC 업무 통합 플랫폼")

    tab_login, tab_signup = st.tabs(["로그인", "회원가입"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("이메일")
            password = st.text_input("비밀번호", type="password")
            submitted = st.form_submit_button("로그인", use_container_width=True)
            if submitted:
                if not email or not password:
                    st.error("이메일과 비밀번호를 입력해주세요.")
                    return
                _do_login(email, password)

    with tab_signup:
        with st.form("signup_form"):
            new_email = st.text_input("이메일")
            new_password = st.text_input("비밀번호 (8자 이상)", type="password")
            new_password_confirm = st.text_input("비밀번호 확인", type="password")
            display_name = st.text_input("이름 (표시용)")
            submitted = st.form_submit_button("회원가입", use_container_width=True)
            if submitted:
                if not new_email or not new_password:
                    st.error("이메일과 비밀번호를 입력해주세요.")
                    return
                if len(new_password) < 8:
                    st.error("비밀번호는 8자 이상이어야 합니다.")
                    return
                if new_password != new_password_confirm:
                    st.error("비밀번호가 일치하지 않습니다.")
                    return
                _do_signup(new_email, new_password, display_name)


# ── 로그인 / 로그아웃 처리 ────────────────────────────────

def _do_login(email: str, password: str):
    try:
        sb = get_supabase_client()
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = res.user
        st.session_state.session = res.session
        st.session_state.last_activity = time.time()

        if res.session:
            st.session_state._pending_cookies = {
                "access": res.session.access_token,
                "refresh": res.session.refresh_token,
            }

        # 로그인 성공 시 users_settings row 없으면 pending으로 생성
        # (회원가입 시 upsert 실패한 경우 복구)
        if res.user:
            _ensure_settings_row(res.user.id)

        st.rerun()
    except Exception as e:
        err = str(e)
        if "Invalid login" in err or "invalid_credentials" in err:
            st.error("이메일 또는 비밀번호가 올바르지 않습니다.")
        elif "Email not confirmed" in err or "email_not_confirmed" in err:
            st.error("이메일 인증이 필요합니다. 가입 시 받은 이메일을 확인해주세요.")
        else:
            from utils.helpers import safe_error
            st.error(safe_error("로그인", Exception(err)))


def _ensure_settings_row(user_id: str):
    """로그인 성공 후 users_settings row 없으면 pending으로 생성"""
    try:
        sb = get_supabase_client()
        res = sb.table("users_settings").select("id").eq("id", user_id).execute()
        if not res.data:
            from utils.db_admin import get_admin_client
            get_admin_client().table("users_settings").upsert({
                "id": user_id,
                "status": "pending",
                "role": "user",
            }).execute()
    except Exception:
        pass


def _do_signup(email: str, password: str, display_name: str):
    try:
        sb = get_supabase_client()
        res = sb.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"display_name": display_name}},
        })
        if res.user:
            # 가입 후 pending — 관리자 승인 필요
            try:
                from utils.db_admin import get_admin_client
                get_admin_client().table("users_settings").upsert({
                    "id": res.user.id,
                    "display_name": display_name,
                    "status": "pending",
                    "role": "user",
                }).execute()
            except Exception:
                pass
            # 관리자에게 텔레그램 알림
            try:
                from utils.telegram import send_message
                send_message(
                    f"🔔 회원가입 승인 요청\n\n"
                    f"이름: {display_name or '(미입력)'}\n"
                    f"이메일: {email}\n\n"
                    f"설정 > Admin 관리에서 승인해주세요."
                )
            except Exception:
                pass
            st.success("회원가입 신청이 완료되었습니다. 관리자 승인 후 이용 가능합니다.")
        else:
            st.warning("회원가입 요청이 전송되었습니다. 이메일을 확인해주세요.")
    except Exception as e:
        msg = str(e)
        if "already registered" in msg:
            st.error("이미 등록된 이메일입니다.")
        else:
            from utils.helpers import safe_error
            st.error(safe_error("회원가입", Exception(msg)))


def logout():
    """로그아웃 — Supabase 세션 + 쿠키 삭제"""
    try:
        sb = get_supabase_client()
        sb.auth.sign_out()
    except Exception:
        pass
    ctrl = _ctrl()
    if ctrl:
        try:
            ctrl.remove(_COOKIE_ACCESS)
            ctrl.remove(_COOKIE_REFRESH)
        except Exception:
            pass
    st.session_state.clear()
    st.rerun()
