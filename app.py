"""FCPilot — 메인 라우터 (로직 넣지 말 것)"""
import streamlit as st
from config import PAGE_CONFIG
from auth import is_logged_in, show_login_page, logout, check_session_timeout

st.set_page_config(**PAGE_CONFIG)


def main():
    if not is_logged_in():
        show_login_page()
        return

    check_session_timeout()

    # 사이드바
    with st.sidebar:
        st.title("🛡️ FCPilot")
        user = st.session_state.get("user")
        if user:
            st.caption(f"📧 {user.email}")

        tab = st.radio(
            "메뉴",
            ["📊 보장분석", "⚙️ 설정"],
            label_visibility="collapsed",
        )

        st.divider()
        if st.button("로그아웃", use_container_width=True):
            logout()

    # 페이지 라우팅
    if tab == "📊 보장분석":
        from pages.page_analysis import render
        render()
    elif tab == "⚙️ 설정":
        from pages.page_settings import render
        render()


if __name__ == "__main__":
    main()
