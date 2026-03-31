"""FCPilot 인증 모듈 — Supabase Auth + 쿠키 기반 세션 유지"""
import time
import streamlit as st
from utils.supabase_client import get_supabase_client
from config import SESSION_TIMEOUT

_COOKIE_ACCESS = "fp_access"
_COOKIE_REFRESH = "fp_refresh"
_COOKIE_MAX_AGE = 30 * 24 * 3600  # 30일


# ── 쿠키 매니저 ──────────────────────────────────────────

def _get_cm():
    """CookieManager 싱글턴 (컴포넌트 key 고정)"""
    try:
        from extra_streamlit_components import CookieManager
        return CookieManager(key="fcpilot_auth_v1")
    except Exception:
        return None


# ── 세션 초기화 ──────────────────────────────────────────

def init_auth():
    """앱 최상단에서 호출 — 세션 없으면 쿠키에서 복원 시도"""
    if st.session_state.get("user"):
        return  # 이미 로그인됨

    cm = _get_cm()
    if cm is None:
        return

    try:
        cookies = cm.get_all()
        access = cookies.get(_COOKIE_ACCESS, "")
        refresh = cookies.get(_COOKIE_REFRESH, "")
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
    except Exception:
        # 토큰 만료 — 쿠키 삭제
        _clear_cookies(cm)


# ── 상태 확인 ─────────────────────────────────────────────

def is_logged_in() -> bool:
    return st.session_state.get("user") is not None


def get_current_user_id() -> str:
    user = st.session_state.get("user")
    return user.id if user else ""


def is_admin() -> bool:
    user_id = get_current_user_id()
    if not user_id:
        return False
    try:
        sb = get_supabase_client()
        res = sb.table("users_settings").select("role").eq("id", user_id).execute()
        if res.data:
            return res.data[0].get("role") == "admin"
    except Exception:
        pass
    return False


def check_session_timeout():
    """60분 무활동 시 자동 로그아웃"""
    if "last_activity" not in st.session_state:
        st.session_state.last_activity = time.time()
        return

    elapsed = time.time() - st.session_state.last_activity
    if elapsed > SESSION_TIMEOUT:
        logout()
        st.warning("60분 동안 활동이 없어 자동 로그아웃되었습니다.")
        st.rerun()
    else:
        st.session_state.last_activity = time.time()


# ── 로그인 UI ─────────────────────────────────────────────

def show_login_page():
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

        # 쿠키에 토큰 저장 (새로고침 후 복원용)
        if res.session:
            cm = _get_cm()
            if cm:
                try:
                    cm.set(_COOKIE_ACCESS, res.session.access_token, max_age=_COOKIE_MAX_AGE)
                    cm.set(_COOKIE_REFRESH, res.session.refresh_token, max_age=_COOKIE_MAX_AGE)
                except Exception:
                    pass

        st.rerun()
    except Exception as e:
        msg = str(e)
        if "Invalid login" in msg:
            st.error("이메일 또는 비밀번호가 올바르지 않습니다.")
        else:
            st.error(f"로그인 실패: {msg}")


def _do_signup(email: str, password: str, display_name: str):
    try:
        sb = get_supabase_client()
        res = sb.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"display_name": display_name}},
        })
        if res.user:
            st.success("회원가입 완료! 이메일 인증 후 로그인해주세요.")
        else:
            st.warning("회원가입 요청이 전송되었습니다. 이메일을 확인해주세요.")
    except Exception as e:
        msg = str(e)
        if "already registered" in msg:
            st.error("이미 등록된 이메일입니다.")
        else:
            st.error(f"회원가입 실패: {msg}")


def logout():
    """로그아웃 — Supabase 세션 + 쿠키 삭제"""
    try:
        sb = get_supabase_client()
        sb.auth.sign_out()
    except Exception:
        pass
    cm = _get_cm()
    if cm:
        _clear_cookies(cm)
    st.session_state.clear()
    st.rerun()


def _clear_cookies(cm):
    try:
        cm.delete(_COOKIE_ACCESS)
        cm.delete(_COOKIE_REFRESH)
    except Exception:
        pass
