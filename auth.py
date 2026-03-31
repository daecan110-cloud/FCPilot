"""FCPilot 인증 모듈 — Supabase Auth"""
import time
import streamlit as st
from utils.supabase_client import get_supabase_client
from config import SESSION_TIMEOUT


def check_session_timeout():
    """60분 무활동 시 자동 로그아웃"""
    if "last_activity" not in st.session_state:
        st.session_state.last_activity = time.time()
        return

    elapsed = time.time() - st.session_state.last_activity
    if elapsed > SESSION_TIMEOUT:
        st.session_state.clear()
        st.warning("60분 동안 활동이 없어 자동 로그아웃되었습니다.")
        st.rerun()
    else:
        st.session_state.last_activity = time.time()


def is_logged_in() -> bool:
    """로그인 상태 확인"""
    return st.session_state.get("user") is not None


def get_current_user_id() -> str:
    """현재 로그인 사용자 ID"""
    user = st.session_state.get("user")
    if user:
        return user.id
    return ""


def show_login_page():
    """로그인/회원가입 UI"""
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


def _do_login(email: str, password: str):
    """로그인 처리"""
    try:
        sb = get_supabase_client()
        res = sb.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
        st.session_state.user = res.user
        st.session_state.session = res.session
        st.session_state.last_activity = time.time()
        st.rerun()
    except Exception as e:
        msg = str(e)
        if "Invalid login" in msg:
            st.error("이메일 또는 비밀번호가 올바르지 않습니다.")
        else:
            st.error(f"로그인 실패: {msg}")


def _do_signup(email: str, password: str, display_name: str):
    """회원가입 처리"""
    try:
        sb = get_supabase_client()
        res = sb.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"display_name": display_name}},
        })
        if res.user:
            # fp_users_settings는 DB 트리거가 자동 생성
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
    """로그아웃"""
    try:
        sb = get_supabase_client()
        sb.auth.sign_out()
    except Exception:
        pass
    st.session_state.clear()
    st.rerun()
